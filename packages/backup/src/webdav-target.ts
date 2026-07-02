import {
  BackupTargetAuthError,
  BackupTargetUnavailableError,
  type BackupObject,
  type BackupObjectTarget,
  assertSafeBackupPath
} from "./target";

export interface WebDavBackupTargetConfig {
  baseUrl: string;
  username?: string;
  password?: string;
  bearerToken?: string;
  fetchImpl?: typeof fetch;
}

function normalizeBaseUrl(baseUrl: string): string {
  const normalized = baseUrl.replace(/\/+$/, "");
  if (!normalized) {
    throw new Error("WebDAV baseUrl is required");
  }
  return normalized;
}

function encodeObjectPath(path: string): string {
  assertSafeBackupPath(path);
  return path
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
}

function buildHeaders(config: WebDavBackupTargetConfig): Headers {
  const headers = new Headers();
  if (config.bearerToken) {
    headers.set("Authorization", `Bearer ${config.bearerToken}`);
    return headers;
  }
  if (config.username || config.password) {
    const token = Buffer.from(`${config.username ?? ""}:${config.password ?? ""}`).toString(
      "base64"
    );
    headers.set("Authorization", `Basic ${token}`);
  }
  return headers;
}

function toRequestBody(data: Uint8Array): ArrayBuffer {
  const body = new ArrayBuffer(data.byteLength);
  new Uint8Array(body).set(data);
  return body;
}

async function ensureSuccess(response: Response, path: string): Promise<void> {
  if (response.ok) {
    return;
  }
  if (response.status === 401 || response.status === 403) {
    throw new BackupTargetAuthError(`WebDAV authentication failed for ${path}`);
  }
  throw new BackupTargetUnavailableError(
    `WebDAV request failed for ${path}: ${response.status} ${response.statusText}`
  );
}

export function createWebDavBackupTarget(
  config: WebDavBackupTargetConfig
): BackupObjectTarget {
  const baseUrl = normalizeBaseUrl(config.baseUrl);
  const fetchImpl = config.fetchImpl ?? fetch;

  return {
    kind: "webdav",
    async putObject(object: BackupObject): Promise<void> {
      const path = encodeObjectPath(object.path);
      const headers = buildHeaders(config);
      headers.set("Content-Type", "application/octet-stream");

      const response = await fetchImpl(`${baseUrl}/${path}`, {
        method: "PUT",
        headers,
        body: toRequestBody(object.data)
      });
      await ensureSuccess(response, object.path);
    },
    async getObject(pathInput: string): Promise<Uint8Array> {
      const path = encodeObjectPath(pathInput);
      const response = await fetchImpl(`${baseUrl}/${path}`, {
        method: "GET",
        headers: buildHeaders(config)
      });
      await ensureSuccess(response, pathInput);
      return new Uint8Array(await response.arrayBuffer());
    }
  };
}
