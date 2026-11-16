import { spawnSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const backend = fileURLToPath(new URL("../../backend/", import.meta.url));
export const python = fileURLToPath(new URL(
  process.platform === "win32" ? "../../backend/.venv/Scripts/python.exe" : "../../backend/.venv/bin/python",
  import.meta.url,
));

export async function exportSchema(executable = python, target) {
  const result = spawnSync(executable, ["-m", "app.export_openapi"], {
    cwd: backend,
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });
  if (result.error || result.status !== 0) {
    throw new Error("OpenAPI 匯出失敗；請確認 backend/.venv 與既有依賴。", { cause: result.error });
  }
  const schema = JSON.parse(result.stdout);
  if (!schema.openapi || !schema.paths) throw new Error("OpenAPI 匯出內容缺少 openapi 或 paths。");
  if (target) await writeFile(target, JSON.stringify(schema, null, 2) + "\n", "utf8");
  return schema;
}

export async function renderTypes(schema) {
  // 有 default 不等於請求必填；必填與否只依 OpenAPI required。
  return "// 由 npm run types:generate 產生，請勿手動編輯。\n" +
    astToString(await openapiTS(schema, { defaultNonNullable: false }));
}

export async function generateTypes(schema, target) {
  await writeFile(target, await renderTypes(schema), "utf8");
}

export async function checkGenerated(schema, target) {
  const current = (await readFile(target, "utf8")).replace(/\r\n/g, "\n");
  if (current !== await renderTypes(schema)) {
    throw new Error("產生型別已過期，請執行 npm run types:generate。");
  }
}

export function checkPendingResponses(schema, pendingText) {
  const entries = [...pendingText.matchAll(/^\/\/ pending-response: (GET|POST|PUT|PATCH|DELETE) (\S+)$/gm)];
  if (!entries.length) {
    if (!/^\/\/ pending-response-count: 0$/m.test(pendingText)) throw new Error("types.pending.ts 缺少 pending-response 清單。");
    for (const [path, item] of Object.entries(schema.paths)) {
      for (const [method, operation] of Object.entries(item)) {
        if (!["get", "post", "put", "patch", "delete", "head", "options", "trace"].includes(method)) continue;
        for (const [status, response] of Object.entries(operation.responses ?? {})) {
          if (!/^2(?:\d\d|XX)$/i.test(status)) continue;
          const media = Object.values(response.content ?? {});
          if (!response.$ref && (!media.length || media.some(({ schema: body }) => !body || (typeof body === "object" && !Object.keys(body).length)))) {
            throw new Error(`${method.toUpperCase()} ${path} 的 ${status} 回應尚無模型，不能宣告 pending-response-count: 0。`);
          }
        }
      }
    }
    return 0;
  }
  for (const [, method, path] of entries) {
    const operation = schema.paths[path]?.[method.toLowerCase()];
    if (!operation) throw new Error(`pending-response 端點不存在：${method} ${path}`);
    for (const [status, response] of Object.entries(operation.responses ?? {})) {
      if (!/^2(?:\d\d|XX)$/i.test(status)) continue;
      const modeled = response.$ref || Object.values(response.content ?? {}).some(({ schema: body }) =>
        body !== undefined && (typeof body !== "object" || body === null || Object.keys(body).length > 0),
      );
      if (modeled) {
        throw new Error(`${method} ${path} 的 ${status} 回應已有模型，請移除 types.pending.ts 對應手寫型別與清單項目。`);
      }
    }
  }
  return entries.length;
}
