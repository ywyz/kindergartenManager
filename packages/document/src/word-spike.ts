import {
  AlignmentType,
  BorderStyle,
  Document as DocxDocument,
  ImageRun,
  LineRuleType,
  Packer,
  Paragraph,
  Table,
  TableCell,
  TableLayoutType,
  TableRow,
  TextRun,
  WidthType
} from "docx";

import {
  type WordExportStyleConfig,
  type WordTextStyle,
  mergeWordExportStyleConfig
} from "./word-style";

export interface WordTableInput {
  headers: readonly string[];
  rows: readonly (readonly string[])[];
}

export interface WordImageInput {
  data: Buffer | Uint8Array | ArrayBuffer;
  type: "jpg" | "png" | "gif" | "bmp";
  widthPx: number;
  heightPx: number;
  altText?: string;
}

export interface StyledWordDocumentInput {
  title: string;
  paragraphs: readonly string[];
  table: WordTableInput;
  image?: WordImageInput;
  style?: Partial<WordExportStyleConfig>;
}

function ptToHalfPoints(value: number): number {
  return Math.round(value * 2);
}

function ptToTwips(value: number): number {
  return Math.round(value * 20);
}

function lineSpacingToTwips(value: number): number {
  return Math.round(value * 240);
}

function toAlignment(value: WordTextStyle["alignment"]): (typeof AlignmentType)[keyof typeof AlignmentType] {
  const map = {
    left: AlignmentType.LEFT,
    center: AlignmentType.CENTER,
    right: AlignmentType.RIGHT
  };
  return map[value];
}

function createTextRun(text: string, style: WordTextStyle): TextRun {
  return new TextRun({
    text,
    bold: style.bold,
    color: style.color.toUpperCase(),
    size: ptToHalfPoints(style.fontSizePt),
    font: {
      ascii: style.fontFamily,
      hAnsi: style.fontFamily,
      eastAsia: style.fontFamily,
      cs: style.fontFamily
    }
  });
}

function createStyledParagraph(text: string, style: WordTextStyle): Paragraph {
  return new Paragraph({
    alignment: toAlignment(style.alignment),
    spacing: {
      before: ptToTwips(style.spacingBeforePt),
      after: ptToTwips(style.spacingAfterPt),
      line: lineSpacingToTwips(style.lineSpacingMultiple),
      lineRule: LineRuleType.AUTO
    },
    children: [createTextRun(text, style)]
  });
}

function createTableCell(text: string, style: WordTextStyle): TableCell {
  return new TableCell({
    margins: {
      top: 120,
      bottom: 120,
      left: 120,
      right: 120
    },
    children: [createStyledParagraph(text, style)]
  });
}

function createTable(input: WordTableInput, style: WordExportStyleConfig): Table {
  const header = new TableRow({
    tableHeader: true,
    children: input.headers.map((item) => createTableCell(item, style.tableHeader))
  });
  const rows = input.rows.map(
    (row) =>
      new TableRow({
        children: row.map((item) => createTableCell(item, style.body))
      })
  );

  return new Table({
    width: {
      size: 100,
      type: WidthType.PERCENTAGE
    },
    layout: TableLayoutType.AUTOFIT,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 1, color: "D1D5DB" },
      bottom: { style: BorderStyle.SINGLE, size: 1, color: "D1D5DB" },
      left: { style: BorderStyle.SINGLE, size: 1, color: "D1D5DB" },
      right: { style: BorderStyle.SINGLE, size: 1, color: "D1D5DB" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: "D1D5DB" },
      insideVertical: { style: BorderStyle.SINGLE, size: 1, color: "D1D5DB" }
    },
    rows: [header, ...rows]
  });
}

function createImageParagraph(image: WordImageInput): Paragraph {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [
      new ImageRun({
        type: image.type,
        data: image.data,
        transformation: {
          width: image.widthPx,
          height: image.heightPx
        },
        altText: {
          name: image.altText ?? "export-image",
          title: image.altText ?? "export-image",
          description: image.altText ?? "export-image"
        }
      })
    ]
  });
}

export async function generateStyledWordDocument(
  input: StyledWordDocumentInput
): Promise<Buffer> {
  const style = mergeWordExportStyleConfig(input.style);
  const children = [
    createStyledParagraph(input.title, style.title),
    ...input.paragraphs.map((paragraph) => createStyledParagraph(paragraph, style.body)),
    createTable(input.table, style)
  ];

  if (input.image) {
    children.push(createImageParagraph(input.image));
  }

  const document = new DocxDocument({
    sections: [
      {
        children
      }
    ]
  });

  return Packer.toBuffer(document);
}
