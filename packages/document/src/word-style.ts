import { z } from "zod";

export const WordAlignmentSchema = z.enum(["left", "center", "right"]);

export const WordTextStyleSchema = z.object({
  fontFamily: z.string().min(1),
  fontSizePt: z.number().min(6).max(72),
  bold: z.boolean().default(false),
  color: z.string().regex(/^[0-9A-Fa-f]{6}$/).default("000000"),
  alignment: WordAlignmentSchema.default("left"),
  spacingBeforePt: z.number().min(0).max(120).default(0),
  spacingAfterPt: z.number().min(0).max(120).default(0),
  lineSpacingMultiple: z.number().min(1).max(3).default(1)
});

export type WordTextStyle = z.infer<typeof WordTextStyleSchema>;

export const WordExportStyleConfigSchema = z.object({
  title: WordTextStyleSchema,
  tableHeader: WordTextStyleSchema,
  body: WordTextStyleSchema
});

export type WordExportStyleConfig = z.infer<typeof WordExportStyleConfigSchema>;

export const DEFAULT_WORD_EXPORT_STYLE_CONFIG = WordExportStyleConfigSchema.parse({
  title: {
    fontFamily: "Microsoft YaHei",
    fontSizePt: 18,
    bold: true,
    color: "111827",
    alignment: "center",
    spacingBeforePt: 0,
    spacingAfterPt: 12,
    lineSpacingMultiple: 1.2
  },
  tableHeader: {
    fontFamily: "Microsoft YaHei",
    fontSizePt: 11,
    bold: true,
    color: "111827",
    alignment: "center",
    spacingBeforePt: 3,
    spacingAfterPt: 3,
    lineSpacingMultiple: 1.15
  },
  body: {
    fontFamily: "SimSun",
    fontSizePt: 11,
    bold: false,
    color: "111827",
    alignment: "left",
    spacingBeforePt: 0,
    spacingAfterPt: 6,
    lineSpacingMultiple: 1.5
  }
});

export function mergeWordExportStyleConfig(
  overrides: Partial<WordExportStyleConfig> = {}
): WordExportStyleConfig {
  return WordExportStyleConfigSchema.parse({
    title: {
      ...DEFAULT_WORD_EXPORT_STYLE_CONFIG.title,
      ...overrides.title
    },
    tableHeader: {
      ...DEFAULT_WORD_EXPORT_STYLE_CONFIG.tableHeader,
      ...overrides.tableHeader
    },
    body: {
      ...DEFAULT_WORD_EXPORT_STYLE_CONFIG.body,
      ...overrides.body
    }
  });
}
