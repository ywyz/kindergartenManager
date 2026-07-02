import { describe, expect, it } from "vitest";

import {
  SecretCryptoError,
  decryptSecret,
  encryptSecret,
  maskSecret,
  redactSecretsFromText
} from "./secret-crypto";

const aad = {
  tenantId: 1,
  userId: 7,
  keyKind: "text" as const
};

describe("AI key secret crypto", () => {
  it("encrypts and decrypts without exposing plaintext in the record", () => {
    const record = encryptSecret({
      plaintext: "sk-live-secret-value",
      masterKey: "master-key",
      keyVersion: "v1",
      aad
    });

    expect(JSON.stringify(record)).not.toContain("sk-live-secret-value");
    expect(record.algorithm).toBe("aes-256-gcm");
    expect(decryptSecret({ record, masterKey: "master-key", aad })).toBe(
      "sk-live-secret-value"
    );
  });

  it("uses a random iv so encrypting the same value twice produces different ciphertext", () => {
    const first = encryptSecret({
      plaintext: "sk-live-secret-value",
      masterKey: "master-key",
      keyVersion: "v1",
      aad
    });
    const second = encryptSecret({
      plaintext: "sk-live-secret-value",
      masterKey: "master-key",
      keyVersion: "v1",
      aad
    });

    expect(first.iv).not.toBe(second.iv);
    expect(first.ciphertext).not.toBe(second.ciphertext);
  });

  it("binds ciphertext to tenant, user, and AI key kind through AAD", () => {
    const record = encryptSecret({
      plaintext: "sk-live-secret-value",
      masterKey: "master-key",
      keyVersion: "v1",
      aad
    });

    expect(() =>
      decryptSecret({
        record,
        masterKey: "master-key",
        aad: { ...aad, tenantId: 2 }
      })
    ).toThrow(SecretCryptoError);

    expect(() =>
      decryptSecret({
        record,
        masterKey: "master-key",
        aad: { ...aad, userId: 8 }
      })
    ).toThrow(SecretCryptoError);

    expect(() =>
      decryptSecret({
        record,
        masterKey: "master-key",
        aad: { ...aad, keyKind: "vision" }
      })
    ).toThrow(SecretCryptoError);
  });

  it("rejects wrong master keys", () => {
    const record = encryptSecret({
      plaintext: "sk-live-secret-value",
      masterKey: "master-key",
      keyVersion: "v1",
      aad
    });

    expect(() => decryptSecret({ record, masterKey: "wrong-key", aad })).toThrow(
      SecretCryptoError
    );
  });

  it("masks secrets and redacts known secrets from log text", () => {
    expect(maskSecret("sk-live-secret-value")).toBe("sk-****alue");
    expect(
      redactSecretsFromText("request failed for sk-live-secret-value", [
        "sk-live-secret-value"
      ])
    ).toBe("request failed for [REDACTED_SECRET]");
  });
});
