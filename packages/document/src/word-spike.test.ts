import JSZip from "jszip";
import { describe, expect, it } from "vitest";

import {
  DEFAULT_WORD_EXPORT_STYLE_CONFIG,
  WordExportStyleConfigSchema,
  generateStyledWordDocument
} from ".";

const png1x1 = Uint8Array.from([
  0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
  0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
  0x08, 0x06, 0x00, 0x00, 0x00, 0x1f, 0x15, 0xc4, 0x89, 0x00, 0x00, 0x00,
  0x0a, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9c, 0x63, 0x00, 0x01, 0x00, 0x00,
  0x05, 0x00, 0x01, 0x0d, 0x0a, 0x2d, 0xb4, 0x00, 0x00, 0x00, 0x00, 0x49,
  0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82
]);

async function readDocxXml(buffer: Buffer): Promise<{
  documentXml: string;
  relationshipXml: string;
  mediaFiles: readonly string[];
}> {
  const archive = await JSZip.loadAsync(buffer);
  const documentXml = await archive.file("word/document.xml")?.async("string");
  const relationshipXml = await archive
    .file("word/_rels/document.xml.rels")
    ?.async("string");

  if (!documentXml || !relationshipXml) {
    throw new Error("Generated docx is missing document XML");
  }

  return {
    documentXml,
    relationshipXml,
    mediaFiles: Object.keys(archive.files).filter(
      (name) => name.startsWith("word/media/") && !archive.files[name]?.dir
    )
  };
}

describe("generateStyledWordDocument", () => {
  it("generates a docx with Chinese text, table, image, and adjustable styles", async () => {
    const buffer = await generateStyledWordDocument({
      title: "幼儿观察记录",
      paragraphs: ["幼儿能主动描述游戏过程。"],
      table: {
        headers: ["观察项", "记录"],
        rows: [["语言表达", "能使用完整句子"]]
      },
      image: {
        type: "png",
        data: png1x1,
        widthPx: 24,
        heightPx: 24,
        altText: "观察照片"
      },
      style: {
        title: {
          ...DEFAULT_WORD_EXPORT_STYLE_CONFIG.title,
          fontFamily: "KaiTi",
          fontSizePt: 20,
          spacingAfterPt: 10,
          lineSpacingMultiple: 1.25
        },
        tableHeader: {
          ...DEFAULT_WORD_EXPORT_STYLE_CONFIG.tableHeader,
          fontFamily: "SimHei",
          fontSizePt: 12,
          spacingBeforePt: 2,
          spacingAfterPt: 2,
          lineSpacingMultiple: 1.1
        },
        body: {
          ...DEFAULT_WORD_EXPORT_STYLE_CONFIG.body,
          fontFamily: "FangSong",
          fontSizePt: 10.5,
          spacingBeforePt: 1,
          spacingAfterPt: 8,
          lineSpacingMultiple: 1.75
        }
      }
    });

    const { documentXml, relationshipXml, mediaFiles } = await readDocxXml(buffer);

    expect(documentXml).toContain("幼儿观察记录");
    expect(documentXml).toContain("幼儿能主动描述游戏过程。");
    expect(documentXml).toContain("观察项");
    expect(documentXml).toContain("能使用完整句子");
    expect(documentXml).toContain("<w:tbl>");
    expect(documentXml).toContain("<w:drawing>");
    expect(relationshipXml).toContain("relationships/image");
    expect(mediaFiles).toHaveLength(1);

    expect(documentXml).toContain('w:eastAsia="KaiTi"');
    expect(documentXml).toContain('w:eastAsia="SimHei"');
    expect(documentXml).toContain('w:eastAsia="FangSong"');
    expect(documentXml).toContain('w:sz w:val="40"');
    expect(documentXml).toContain('w:sz w:val="24"');
    expect(documentXml).toContain('w:sz w:val="21"');
    expect(documentXml).toContain('w:line="300"');
    expect(documentXml).toContain('w:line="264"');
    expect(documentXml).toContain('w:line="420"');
    expect(documentXml).toContain('w:after="200"');
    expect(documentXml).toContain('w:after="160"');
  });

  it("rejects invalid style values before generating docx", () => {
    expect(() =>
      WordExportStyleConfigSchema.parse({
        title: {
          ...DEFAULT_WORD_EXPORT_STYLE_CONFIG.title,
          fontSizePt: 4
        },
        tableHeader: DEFAULT_WORD_EXPORT_STYLE_CONFIG.tableHeader,
        body: DEFAULT_WORD_EXPORT_STYLE_CONFIG.body
      })
    ).toThrow();
  });
});
