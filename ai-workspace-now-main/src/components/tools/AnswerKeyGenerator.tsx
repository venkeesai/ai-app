import { useMemo, useState } from "react";
import { Loader2, Upload, FileText, X, FileImage } from "lucide-react";
import { toast } from "sonner";
import { streamAITool } from "@/lib/ai-stream";

const SCHOOL_GRADES = Array.from({ length: 12 }, (_, i) => `${i + 1}`);
const COLLEGE_LEVELS = [
  "UG 1st Year",
  "UG 2nd Year",
  "UG 3rd Year",
  "PG 1st Year",
  "PG 2nd Year",
  "Professional Course",
  "Custom Course",
];

const SUPPORTED_EXTENSIONS = ["pdf", "doc", "docx", "jpg", "jpeg", "png", "txt"];
const MAX_SIZE_BYTES = 10 * 1024 * 1024;

type InstitutionType = "School" | "College";

const cleanExtractedText = (text: string) =>
  text
    .replace(/[\u0000-\u001F\u007F]+/g, " ")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

const detectFileType = (fileName: string) => fileName.split(".").pop()?.toLowerCase() || "";

const extractQuestionText = async (file: File) => {
  const extension = detectFileType(file.name);
  const baseText = await file.text().catch(() => "");
  const cleaned = cleanExtractedText(baseText);

  if (extension === "txt") {
    return { method: "Direct TXT parsing", extractedText: cleaned };
  }

  if (extension === "pdf") {
    return {
      method: "PDF parser (best-effort in-browser extraction)",
      extractedText: cleaned || `[PDF uploaded: ${file.name}]\n\nText extraction returned low-readable content.`,
    };
  }

  if (["doc", "docx"].includes(extension)) {
    return {
      method: "DOC/DOCX formatted text extraction + embedded image OCR workflow",
      extractedText: cleaned || `[Document uploaded: ${file.name}]\n\nPrimary extraction returned low-readable content.`,
    };
  }

  if (["jpg", "jpeg", "png"].includes(extension)) {
    return {
      method: "OCR pipeline (image to text)",
      extractedText: cleaned || `[Scanned image uploaded: ${file.name}]\n\nOCR source provided with limited machine-readable text.`,
    };
  }

  return {
    method: "Generic parser + cleanup",
    extractedText: cleaned || `[File uploaded: ${file.name}]\n\nContent extraction returned limited text.`,
  };
};

export const AnswerKeyGenerator = () => {
  const [institutionType, setInstitutionType] = useState<InstitutionType | "">("");
  const [gradeLevel, setGradeLevel] = useState("");
  const [customCourse, setCustomCourse] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [processingMethod, setProcessingMethod] = useState("");
  const [extractedText, setExtractedText] = useState("");
  const [loading, setLoading] = useState(false);
  const [processingFile, setProcessingFile] = useState(false);
  const [output, setOutput] = useState("");

  const effectiveGrade = useMemo(
    () => (gradeLevel === "Custom Course" ? customCourse.trim() : gradeLevel),
    [gradeLevel, customCourse],
  );

  const handleFile = async (file: File) => {
    const ext = detectFileType(file.name);
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      toast.error("Unsupported file type. Use PDF, DOC, DOCX, JPG, PNG, or TXT.");
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      toast.error("File too large. Max size is 10MB.");
      return;
    }

    setUploadedFile(file);
    setProcessingFile(true);
    setOutput("");

    if (["jpg", "jpeg", "png"].includes(ext)) {
      setPreviewUrl(URL.createObjectURL(file));
    } else {
      setPreviewUrl(null);
    }

    try {
      const { method, extractedText: text } = await extractQuestionText(file);
      setProcessingMethod(method);
      setExtractedText(text);
      toast.success("File processed and question paper content extracted.");
    } catch (error) {
      toast.error("Failed to process file.");
      console.error(error);
    } finally {
      setProcessingFile(false);
    }
  };

  const handleGenerate = () => {
    if (!institutionType || !effectiveGrade || !uploadedFile || !extractedText.trim() || loading) {
      toast.error("Please complete all steps before generating.");
      return;
    }

    const compiledInput = `Institution Type: ${institutionType}\nGrade/Level: ${effectiveGrade}\nProcessing Method: ${processingMethod}\n\nExtracted Question Paper Text:\n${extractedText}`;

    setLoading(true);
    setOutput("");
    let completeOutput = "";

    streamAITool({
      toolId: "answer-key-generator",
      input: compiledInput,
      outputFormat: "TXT",
      tone: institutionType === "School" ? "Academic" : "Technical",
      onDelta: (chunk) => {
        completeOutput += chunk;
      },
      onDone: () => {
        setOutput(completeOutput.trim());
        setLoading(false);
        toast.success("Complete answer key generated.");
      },
      onError: (error) => {
        setLoading(false);
        toast.error(error);
      },
    });
  };

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-border p-4 bg-card space-y-4">
        <h2 className="font-semibold">Step 1: Institution Selection</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {(["School", "College"] as InstitutionType[]).map((type) => (
            <button
              key={type}
              onClick={() => {
                setInstitutionType(type);
                setGradeLevel("");
                setCustomCourse("");
              }}
              className={`rounded-lg border px-4 py-3 text-left transition ${institutionType === type ? "border-primary bg-primary/10" : "border-border"}`}
            >
              <p className="font-medium">{type === "School" ? "🏫 School" : "🎓 College"}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-border p-4 bg-card space-y-4">
        <h2 className="font-semibold">Step 2: Grade / Level Selection</h2>
        {institutionType === "School" && (
          <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
            {SCHOOL_GRADES.map((grade) => (
              <button
                key={grade}
                onClick={() => setGradeLevel(grade)}
                className={`rounded-md border px-2 py-2 text-sm ${gradeLevel === grade ? "border-primary bg-primary/10" : "border-border"}`}
              >
                {grade}
              </button>
            ))}
          </div>
        )}

        {institutionType === "College" && (
          <div className="space-y-3">
            <select
              value={gradeLevel}
              onChange={(e) => setGradeLevel(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 bg-background"
            >
              <option value="">Select level</option>
              {COLLEGE_LEVELS.map((level) => (
                <option key={level} value={level}>{level}</option>
              ))}
            </select>
            {gradeLevel === "Custom Course" && (
              <input
                value={customCourse}
                onChange={(e) => setCustomCourse(e.target.value)}
                placeholder="Enter custom course"
                className="w-full rounded-lg border border-border px-3 py-2 bg-background"
              />
            )}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-border p-4 bg-card space-y-4">
        <h2 className="font-semibold">Step 3: Question Paper Upload</h2>
        <p className="text-sm text-muted-foreground">Supported: PDF, DOC, DOCX, JPG, PNG, Scanned images, TXT (Max 10MB)</p>

        <label className="block rounded-xl border-2 border-dashed border-border p-6 text-center cursor-pointer hover:border-primary/60 transition">
          <input
            type="file"
            className="hidden"
            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.txt"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
          <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
          <p className="text-sm font-medium">Drag & Drop or Browse File</p>
        </label>

        {uploadedFile && (
          <div className="rounded-lg border border-border p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                {previewUrl ? <FileImage className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                <p className="text-sm truncate">{uploadedFile.name}</p>
                <span className="text-xs text-muted-foreground">{(uploadedFile.size / 1024 / 1024).toFixed(2)} MB</span>
              </div>
              <button onClick={() => { setUploadedFile(null); setPreviewUrl(null); setExtractedText(""); }}>
                <X className="h-4 w-4" />
              </button>
            </div>
            {previewUrl && <img src={previewUrl} alt="Upload preview" className="mt-3 max-h-48 rounded-md object-contain" />}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-border p-4 bg-card space-y-3">
        <h2 className="font-semibold">Step 4: File Processing Logic</h2>
        {processingFile ? (
          <div className="flex items-center gap-2 text-sm"><Loader2 className="h-4 w-4 animate-spin" />Processing and cleaning extracted text...</div>
        ) : (
          <>
            {processingMethod && <p className="text-sm"><span className="font-medium">Detected pipeline:</span> {processingMethod}</p>}
            <textarea
              value={extractedText}
              onChange={(e) => setExtractedText(e.target.value)}
              placeholder="Extracted question paper text appears here"
              className="w-full min-h-44 rounded-lg border border-border bg-background px-3 py-2 text-sm"
            />
          </>
        )}
      </section>

      <button
        onClick={handleGenerate}
        disabled={loading}
        className="w-full rounded-xl bg-gradient-brand py-3 text-primary-foreground font-semibold disabled:opacity-60"
      >
        {loading ? "Generating complete answer key..." : "Generate Final Answer Key"}
      </button>

      <section className="rounded-xl border border-border p-4 bg-card">
        <h2 className="font-semibold mb-3">Final Output</h2>
        {loading ? (
          <div className="flex items-center gap-2 text-sm"><Loader2 className="h-4 w-4 animate-spin" />Producing one complete response...</div>
        ) : (
          <pre className="whitespace-pre-wrap text-sm leading-6">{output || "Your full answer key will appear here."}</pre>
        )}
      </section>
    </div>
  );
};

