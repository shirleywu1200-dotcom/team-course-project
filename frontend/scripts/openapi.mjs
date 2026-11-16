import { readFile } from "node:fs/promises";
import { checkGenerated, checkPendingResponses, exportSchema, generateTypes } from "./openapi-tools.mjs";

const snapshot = new URL("../openapi.json", import.meta.url);
const generated = new URL("../src/api/types.generated.ts", import.meta.url);
const pending = new URL("../src/api/types.pending.ts", import.meta.url);

try {
  const command = process.argv[2];
  if (command === "export") {
    await exportSchema(undefined, snapshot);
    console.log("OpenAPI 已匯出至 frontend/openapi.json（UTF-8）。");
  } else if (["generate", "check", "check-export"].includes(command)) {
    const schema = JSON.parse(await readFile(snapshot, "utf8"));
    if (command === "check-export") {
      const fresh = await exportSchema();
      if (JSON.stringify(fresh) !== JSON.stringify(schema)) {
        throw new Error("OpenAPI 快照已過期，請執行 npm run openapi:export，再執行 npm run types:generate。");
      }
    }
    const pendingCount = checkPendingResponses(schema, await readFile(pending, "utf8"));
    if (command === "generate") {
      await generateTypes(schema, generated);
      console.log("型別已產生至 src/api/types.generated.ts。");
    } else {
      await checkGenerated(schema, generated);
      console.log(`產生型別與暫存回應清單檢查通過。pending 端點：${pendingCount}。` + (command === "check-export" ? " OpenAPI 快照與後端相符。" : ""));
    }
  } else {
    throw new Error("用法：node scripts/openapi.mjs export|generate|check|check-export");
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
