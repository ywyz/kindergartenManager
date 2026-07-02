import {
  createCipheriv,
  createDecipheriv,
  createHash,
  randomBytes
} from "node:crypto";

export type AiKeyKind = "text" | "vision";

export interface SecretAdditionalData {
  tenantId: number;
  userId: number;
  keyKind: AiKeyKind;
}

export interface EncryptedSecretRecord {
  algorithm: "aes-256-gcm";
  keyVersion: string;
  iv: string;
  ciphertext: string;
  authTag: string;
}

export interface EncryptSecretInput {
  plaintext: string;
  masterKey: string;
  keyVersion: string;
  aad: SecretAdditionalData;
}

export interface DecryptSecretInput {
  record: EncryptedSecretRecord;
  masterKey: string;
  aad: SecretAdditionalData;
}

export class SecretCryptoError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SecretCryptoError";
  }
}

function requireNonEmpty(value: string, field: string): void {
  if (!value) {
    throw new SecretCryptoError(`${field} is required`);
  }
}

function deriveKey(masterKey: string, keyVersion: string): Buffer {
  requireNonEmpty(masterKey, "masterKey");
  requireNonEmpty(keyVersion, "keyVersion");
  return createHash("sha256")
    .update("kindergarten-manager-dev4-secret-key")
    .update("\0")
    .update(keyVersion)
    .update("\0")
    .update(masterKey)
    .digest();
}

function aadBuffer(aad: SecretAdditionalData): Buffer {
  if (!Number.isInteger(aad.tenantId) || aad.tenantId <= 0) {
    throw new SecretCryptoError("aad.tenantId must be a positive integer");
  }
  if (!Number.isInteger(aad.userId) || aad.userId <= 0) {
    throw new SecretCryptoError("aad.userId must be a positive integer");
  }
  return Buffer.from(`${aad.tenantId}:${aad.userId}:${aad.keyKind}`, "utf8");
}

export function encryptSecret(input: EncryptSecretInput): EncryptedSecretRecord {
  requireNonEmpty(input.plaintext, "plaintext");

  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", deriveKey(input.masterKey, input.keyVersion), iv);
  cipher.setAAD(aadBuffer(input.aad));

  const ciphertext = Buffer.concat([
    cipher.update(input.plaintext, "utf8"),
    cipher.final()
  ]);

  return {
    algorithm: "aes-256-gcm",
    keyVersion: input.keyVersion,
    iv: iv.toString("base64url"),
    ciphertext: ciphertext.toString("base64url"),
    authTag: cipher.getAuthTag().toString("base64url")
  };
}

export function decryptSecret(input: DecryptSecretInput): string {
  if (input.record.algorithm !== "aes-256-gcm") {
    throw new SecretCryptoError(`Unsupported secret algorithm: ${input.record.algorithm}`);
  }

  try {
    const decipher = createDecipheriv(
      "aes-256-gcm",
      deriveKey(input.masterKey, input.record.keyVersion),
      Buffer.from(input.record.iv, "base64url")
    );
    decipher.setAAD(aadBuffer(input.aad));
    decipher.setAuthTag(Buffer.from(input.record.authTag, "base64url"));

    return Buffer.concat([
      decipher.update(Buffer.from(input.record.ciphertext, "base64url")),
      decipher.final()
    ]).toString("utf8");
  } catch (error) {
    if (error instanceof SecretCryptoError) {
      throw error;
    }
    throw new SecretCryptoError("Unable to decrypt secret");
  }
}

export function maskSecret(secret: string, visibleSuffix = 4): string {
  if (!secret) {
    return "";
  }
  const suffix = secret.slice(-visibleSuffix);
  return `sk-****${suffix}`;
}

export function redactSecretsFromText(text: string, secrets: readonly string[]): string {
  return secrets.reduce((result, secret) => {
    if (!secret) {
      return result;
    }
    return result.split(secret).join("[REDACTED_SECRET]");
  }, text);
}
