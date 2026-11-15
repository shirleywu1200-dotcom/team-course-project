-- 0003 系統種子（PR #1 審查 B2；種子文字經產品負責人 2026-11-15 確認，修改文字屬規格變更）
-- 冪等：重跑、降級再升級都不產生重複列（AC-59）。其餘設定欄位用 DDL 預設值。

INSERT INTO rubrics (version, levels, source, created_at) VALUES
 (0, '["未達成：完成條件大部分沒有達到，需要重做或補做。",
       "部分達成：完成條件只達到一部分，仍缺少重要項目。",
       "符合預設：完成條件達到，品質與事前預期一致。",
       "優於預設：完成條件達到，且品質或完整度優於事前預期。",
       "遠超預設：成果明顯超出原本範圍或預期，可作為範例。"]'::jsonb,
  'default', now())
ON CONFLICT (version) DO NOTHING;

INSERT INTO settings (id, energy_def_high, energy_def_mid, energy_def_low) VALUES
 (1, '需要長時間專注、做判斷或創作；做完需要休息才能接著做別的事。',
     '需要集中注意力，但被打斷後能接續；做完仍有餘力。',
     '照流程或慣例即可完成，不太需要思考；可利用零碎時間做。')
ON CONFLICT (id) DO NOTHING;
