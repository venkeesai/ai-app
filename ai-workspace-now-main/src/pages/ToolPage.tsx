import { useParams, useNavigate } from "react-router-dom";
import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft, Upload, Settings2, Download, Copy, Send, RotateCcw,
  Sparkles, Loader2, Check, ChevronDown, FileText, FileCode, Globe,
  Image as ImageIcon, X, Film, Play,
} from "lucide-react";
import { tools, categories } from "@/data/tools";
import { streamAITool, downloadAsFile, downloadAsHTML } from "@/lib/ai-stream";
import {
  generatePPTX, generatePDF, generateDOCX, removeBackground,
  parsePresentationFromAI,
} from "@/lib/file-generators";
import { toast } from "sonner";
import { AnswerKeyGenerator } from "@/components/tools/AnswerKeyGenerator";

// Tools that produce structured file output (not just text)
const PPTX_TOOLS = ["pitch-deck"];
const PDF_TOOLS = [
  "resume-builder", "cover-letter", "business-plan", "invoice-gen",
  "contract-gen", "swot-analysis", "report-gen", "proposal-writer",
  "meeting-notes", "lesson-plan", "study-guide", "flashcard-gen",
  "quiz-maker",
];
const DOCX_TOOLS = ["article-writer", "speech-writer", "seo-writer"];
const IMAGE_PROCESS_TOOLS = ["bg-remover"];
const IMAGE_GEN_TOOLS = [
  "image-gen", "logo-maker", "icon-gen", "banner-maker", "avatar-gen",
  "thumbnail-maker", "meme-gen", "infographic",
];
const VIDEO_GEN_TOOLS = ["video-gen"];

interface VideoScene {
  sceneNumber: number;
  title: string;
  narration: string;
  imagePrompt: string;
  durationSeconds: number;
  imageUrl?: string;
}

const ToolPage = () => {
  const { toolId } = useParams();
  const navigate = useNavigate();
  const tool = tools.find((t) => t.id === toolId);
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [outputFormat, setOutputFormat] = useState("");
  const [tone, setTone] = useState("Professional");
  const outputRef = useRef<HTMLDivElement>(null);

  // File upload state
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [bgProgress, setBgProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Video gen state
  const [videoDuration, setVideoDuration] = useState(30);
  const [videoScenes, setVideoScenes] = useState<VideoScene[]>([]);
  const [videoProgress, setVideoProgress] = useState("");
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoStep, setVideoStep] = useState(0); // 0=idle, 1=parsing, 2=generating images, 3=stitching, 4=done

  const cat = tool ? categories.find((c) => c.id === tool.category) : null;

  const isImageProcessor = tool && IMAGE_PROCESS_TOOLS.includes(tool.id);
  const isImageGenTool = tool && IMAGE_GEN_TOOLS.includes(tool.id);
  const isPptxTool = tool && PPTX_TOOLS.includes(tool.id);
  const isVideoGenTool = tool && VIDEO_GEN_TOOLS.includes(tool.id);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFile(file);
    setProcessedImage(null);

    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (ev) => setUploadPreview(ev.target?.result as string);
      reader.readAsDataURL(file);
    } else {
      setUploadPreview(null);
    }
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    setUploadPreview(null);
    setProcessedImage(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ─── Background Removal ──────────────────────────────────────────────────
  const handleBgRemoval = useCallback(async () => {
    if (!uploadedFile) {
      toast.error("Please upload an image first");
      return;
    }
    setLoading(true);
    setBgProgress(0);
    setProcessedImage(null);
    try {
      const result = await removeBackground(uploadedFile, (p) => setBgProgress(p));
      const url = URL.createObjectURL(result);
      setProcessedImage(url);
      toast.success("Background removed successfully!");
    } catch (err) {
      toast.error("Background removal failed. Try a different image.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [uploadedFile]);

  // ─── AI Image Generation ──────────────────────────────────────────────────
  const handleImageGen = useCallback(async () => {
    if (!tool || !input.trim()) return;
    setLoading(true);
    setGeneratedImage(null);
    setOutput("");
    try {
      const resp = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/ai-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY}`,
        },
        body: JSON.stringify({ prompt: input, toolId: tool.id }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: "Request failed" }));
        toast.error(err.error || `Error ${resp.status}`);
        return;
      }
      const data = await resp.json();
      if (data.images && data.images.length > 0) {
        setGeneratedImage(data.images[0].image_url.url);
        toast.success("Image generated successfully!");
      } else {
        toast.error("No image was generated. Try a different prompt.");
      }
      if (data.text) setOutput(data.text);
    } catch (err) {
      toast.error("Image generation failed. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [tool, input]);

  // ─── Video Generation ─────────────────────────────────────────────────────
  const handleVideoGen = useCallback(async () => {
    if (!tool || !input.trim()) return;
    setLoading(true);
    setVideoUrl(null);
    setVideoScenes([]);
    setOutput("");

    try {
      // Step 1: Parse script into scenes
      setVideoStep(1);
      setVideoProgress("Analyzing script and planning scenes...");
      const sceneResp = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/ai-video`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY}`,
        },
        body: JSON.stringify({ script: input, duration: videoDuration }),
      });
      if (!sceneResp.ok) {
        const err = await sceneResp.json().catch(() => ({ error: "Failed" }));
        toast.error(err.error || "Scene planning failed");
        setLoading(false);
        setVideoStep(0);
        return;
      }
      const sceneData = await sceneResp.json();
      const scenes: VideoScene[] = sceneData.scenes || [];
      if (scenes.length === 0) {
        toast.error("No scenes generated. Try a more detailed script.");
        setLoading(false);
        setVideoStep(0);
        return;
      }
      setVideoScenes(scenes);

      // Step 2: Generate images for each scene
      setVideoStep(2);
      for (let i = 0; i < scenes.length; i++) {
        setVideoProgress(`Generating scene ${i + 1} of ${scenes.length}: "${scenes[i].title}"...`);
        try {
          const imgResp = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/ai-image`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY}`,
            },
            body: JSON.stringify({ prompt: scenes[i].imagePrompt, toolId: "image-gen" }),
          });
          if (imgResp.ok) {
            const imgData = await imgResp.json();
            if (imgData.images?.[0]?.image_url?.url) {
              scenes[i].imageUrl = imgData.images[0].image_url.url;
            }
          }
        } catch (e) {
          console.error(`Scene ${i + 1} image failed:`, e);
        }
        setVideoScenes([...scenes]);
      }

      const scenesWithImages = scenes.filter(s => s.imageUrl);
      if (scenesWithImages.length === 0) {
        toast.error("Failed to generate scene images. Please try again.");
        setLoading(false);
        setVideoStep(0);
        return;
      }

      // Step 3: Stitch images into video using Canvas + MediaRecorder
      setVideoStep(3);
      setVideoProgress("Composing video from scenes...");

      const canvas = document.createElement("canvas");
      canvas.width = 1280;
      canvas.height = 720;
      const ctx = canvas.getContext("2d")!;

      const stream = canvas.captureStream(30);
      const recorder = new MediaRecorder(stream, { mimeType: "video/webm;codecs=vp9" });
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

      const videoBlob = await new Promise<Blob>((resolve, reject) => {
        recorder.onstop = () => resolve(new Blob(chunks, { type: "video/webm" }));
        recorder.onerror = () => reject(new Error("Recording failed"));
        recorder.start();

        let sceneIdx = 0;
        let frameCount = 0;
        const fps = 30;
        const totalSceneDuration = scenesWithImages.reduce((a, s) => a + (s.durationSeconds || 5), 0);
        const images: HTMLImageElement[] = [];

        // Preload all images
        const loadPromises = scenesWithImages.map((scene, idx) => {
          return new Promise<void>((res) => {
            const img = new window.Image();
            img.crossOrigin = "anonymous";
            img.onload = () => { images[idx] = img; res(); };
            img.onerror = () => { res(); };
            img.src = scene.imageUrl!;
          });
        });

        Promise.all(loadPromises).then(() => {
          const drawFrame = () => {
            if (sceneIdx >= scenesWithImages.length) {
              setTimeout(() => recorder.stop(), 100);
              return;
            }

            const scene = scenesWithImages[sceneIdx];
            const sceneDur = (scene.durationSeconds || 5) * fps;
            const img = images[sceneIdx];

            // Draw image scaled to fill canvas
            ctx.fillStyle = "#000";
            ctx.fillRect(0, 0, 1280, 720);
            if (img) {
              const scale = Math.max(1280 / img.width, 720 / img.height);
              const w = img.width * scale;
              const h = img.height * scale;
              ctx.drawImage(img, (1280 - w) / 2, (720 - h) / 2, w, h);
            }

            // Draw narration text overlay
            const progress = frameCount / sceneDur;
            const fadeIn = Math.min(1, progress * 4);
            const fadeOut = Math.min(1, (1 - progress) * 4);
            const alpha = Math.min(fadeIn, fadeOut);

            ctx.fillStyle = `rgba(0,0,0,${0.5 * alpha})`;
            ctx.fillRect(0, 520, 1280, 200);

            ctx.fillStyle = `rgba(255,255,255,${alpha})`;
            ctx.font = "bold 22px system-ui, sans-serif";
            ctx.textAlign = "center";

            // Word wrap narration
            const words = (scene.narration || scene.title).split(" ");
            let line = "";
            let y = 580;
            for (const word of words) {
              const test = line + word + " ";
              if (ctx.measureText(test).width > 1100 && line) {
                ctx.fillText(line.trim(), 640, y);
                line = word + " ";
                y += 32;
                if (y > 690) break;
              } else {
                line = test;
              }
            }
            if (line.trim() && y <= 690) ctx.fillText(line.trim(), 640, y);

            // Scene title top-left
            ctx.fillStyle = `rgba(255,255,255,${0.7 * alpha})`;
            ctx.font = "16px system-ui, sans-serif";
            ctx.textAlign = "left";
            ctx.fillText(`Scene ${scene.sceneNumber}: ${scene.title}`, 30, 40);

            frameCount++;
            if (frameCount >= sceneDur) {
              sceneIdx++;
              frameCount = 0;
            }

            setVideoProgress(`Rendering: Scene ${sceneIdx + 1}/${scenesWithImages.length} (${Math.round((sceneIdx / scenesWithImages.length) * 100)}%)`);
            requestAnimationFrame(drawFrame);
          };

          drawFrame();
        });
      });

      const url = URL.createObjectURL(videoBlob);
      setVideoUrl(url);
      setVideoStep(4);
      setVideoProgress("Video ready!");
      toast.success("Video generated successfully!");
    } catch (err) {
      console.error("Video gen error:", err);
      toast.error("Video generation failed. Please try again.");
      setVideoStep(0);
    } finally {
      setLoading(false);
    }
  }, [tool, input, videoDuration]);

  // ─── AI Generation ───────────────────────────────────────────────────────
  const handleGenerate = useCallback(() => {
    if (!tool) return;

    if (isImageProcessor) {
      handleBgRemoval();
      return;
    }

    if (isImageGenTool) {
      handleImageGen();
      return;
    }

    if (isVideoGenTool) {
      handleVideoGen();
      return;
    }

    if (!input.trim() || loading) return;
    setLoading(true);
    setOutput("");
    let accumulated = "";

    streamAITool({
      toolId: tool.id,
      input,
      outputFormat: outputFormat || tool.outputFormats[0],
      tone,
      onDelta: (chunk) => {
        accumulated += chunk;
        setOutput(accumulated);
        if (outputRef.current) {
          outputRef.current.scrollTop = outputRef.current.scrollHeight;
        }
      },
      onDone: () => {
        setLoading(false);
        toast.success("Generation complete!");
      },
      onError: (error) => {
        setLoading(false);
        toast.error(error);
      },
    });
  }, [input, loading, tool, outputFormat, tone, isImageProcessor, isImageGenTool, isVideoGenTool, handleBgRemoval, handleImageGen, handleVideoGen]);

  const handleCopy = () => {
    navigator.clipboard.writeText(output);
    setCopied(true);
    toast.success("Copied to clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  // ─── Real File Downloads ──────────────────────────────────────────────────
  const handleDownload = async (format: string) => {
    if (!tool) return;
    const baseName = tool.name.replace(/[^a-zA-Z0-9]/g, "_");

    try {
      switch (format) {
        case "PPTX": {
          const presData = parsePresentationFromAI(output);
          if (presData) {
            toast.info("Generating PowerPoint...");
            await generatePPTX(presData);
            toast.success("PPTX downloaded!");
          } else {
            // Fallback: create simple presentation from text
            await generatePPTX({
              title: tool.name,
              slides: output.split("\n\n").filter(Boolean).map((block, i) => {
                const lines = block.split("\n").filter(Boolean);
                return {
                  title: lines[0]?.replace(/^[#*-]+\s*/, "") || `Slide ${i + 1}`,
                  content: lines.slice(1).map((l) => l.replace(/^[-*•]\s*/, "").replace(/\*\*/g, "")),
                };
              }),
            });
            toast.success("PPTX downloaded!");
          }
          break;
        }
        case "PDF": {
          toast.info("Generating PDF...");
          generatePDF(output, tool.name);
          toast.success("PDF downloaded!");
          break;
        }
        case "DOCX": {
          toast.info("Generating Word document...");
          await generateDOCX(output, tool.name);
          toast.success("DOCX downloaded!");
          break;
        }
        case "PNG": {
          if (generatedImage || processedImage) {
            const imgSrc = generatedImage || processedImage;
            const a = document.createElement("a");
            a.href = imgSrc!;
            a.download = `${baseName}.png`;
            a.click();
            toast.success("PNG downloaded!");
          } else {
            downloadAsFile(output, `${baseName}.png`, "text/plain");
          }
          break;
        }
        case "JPG":
        case "WEBP": {
          if (generatedImage) {
            const a = document.createElement("a");
            a.href = generatedImage;
            a.download = `${baseName}.${format.toLowerCase()}`;
            a.click();
            toast.success(`${format} downloaded!`);
          } else {
            downloadAsFile(output, `${baseName}.${format.toLowerCase()}`, "text/plain");
          }
          break;
        }
        case "HTML":
          downloadAsHTML(output, `${baseName}.html`);
          toast.success("HTML downloaded!");
          break;
        case "JSON":
          downloadAsFile(output, `${baseName}.json`, "application/json");
          toast.success("JSON downloaded!");
          break;
        case "CSV":
          downloadAsFile(output, `${baseName}.csv`, "text/csv");
          toast.success("CSV downloaded!");
          break;
        case "CSS":
          downloadAsFile(output, `${baseName}.css`, "text/css");
          toast.success("CSS downloaded!");
          break;
        case "MD":
          downloadAsFile(output, `${baseName}.md`, "text/markdown");
          toast.success("Markdown downloaded!");
          break;
        case "WEBM":
        case "MP4": {
          if (videoUrl) {
            const a = document.createElement("a");
            a.href = videoUrl;
            a.download = `${baseName}.webm`;
            a.click();
            toast.success("Video downloaded!");
          }
          break;
        }
        default:
          downloadAsFile(output, `${baseName}.txt`, "text/plain");
          toast.success("File downloaded!");
      }
    } catch (err) {
      console.error(err);
      toast.error("Download failed. Please try again.");
    }
  };

  const handleSendToTool = () => {
    toast.info("Select a tool to send this output to", { description: "Navigate to any tool and paste the output" });
    navigator.clipboard.writeText(output);
  };

  if (!tool) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-muted-foreground">Tool not found.</p>
      </div>
    );
  }

  if (tool.id === "answer-key-generator") {
    return (
      <div className="max-w-5xl mx-auto space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4"
        >
          <button onClick={() => navigate(-1)} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-foreground">{tool.name}</h1>
            <p className="text-sm text-muted-foreground">{tool.description}</p>
          </div>
        </motion.div>
        <AnswerKeyGenerator />
      </div>
    );
  }

  const showTextInput = !isImageProcessor;
  const hasOutput = output.length > 0 || processedImage || generatedImage || videoUrl;

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-4 mb-6"
      >
        <button onClick={() => navigate(-1)} className="p-2 rounded-lg hover:bg-muted transition-colors">
          <ArrowLeft className="h-5 w-5 text-muted-foreground" />
        </button>
        <div
          className="h-11 w-11 rounded-xl flex items-center justify-center"
          style={{ backgroundColor: `hsl(${cat?.color || "200 50% 50%"} / 0.12)` }}
        >
          <tool.icon className="h-5 w-5" style={{ color: `hsl(${cat?.color || "200 50% 50%"})` }} />
        </div>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-foreground">{tool.name}</h1>
          <p className="text-sm text-muted-foreground">{tool.description}</p>
        </div>
        <div className="hidden sm:flex items-center gap-1.5">
          {tool.outputFormats.map((f) => (
            <span key={f} className="px-2 py-0.5 rounded-md bg-muted text-xs font-medium text-muted-foreground">{f}</span>
          ))}
        </div>
      </motion.div>

      {/* Two-panel layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Input Panel */}
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-card rounded-2xl border border-border p-5 flex flex-col"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-foreground">Input</h2>
            {showTextInput && <span className="text-xs text-muted-foreground">{input.length} chars</span>}
          </div>

          {/* Text input */}
          {showTextInput && (
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleGenerate(); }}
              placeholder={getPlaceholder(tool.id)}
              rows={8}
              className="flex-1 w-full bg-muted/50 rounded-xl p-4 text-sm text-foreground placeholder:text-muted-foreground resize-none outline-none border border-border/50 focus:border-primary/40 transition-colors font-mono leading-relaxed"
            />
          )}

          {/* Video duration selector */}
          {isVideoGenTool && (
            <div className="mt-3 p-4 bg-muted/30 rounded-xl border border-border/30">
              <label className="text-xs font-medium text-muted-foreground block mb-2">Video Duration (seconds)</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={10}
                  max={120}
                  step={5}
                  value={videoDuration}
                  onChange={(e) => setVideoDuration(Number(e.target.value))}
                  className="flex-1 accent-primary"
                />
                <span className="text-sm font-bold text-foreground min-w-[40px] text-right">{videoDuration}s</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1.5">
                {Math.ceil(videoDuration / 5)} scenes will be generated ({videoDuration}s total)
              </p>
            </div>
          )}

          {/* File upload */}
          {(tool.inputType === "file" || tool.inputType === "both" || isImageProcessor) && (
            <div className="mt-3">
              <input
                ref={fileInputRef}
                type="file"
                accept={isImageProcessor ? "image/*" : "*/*"}
                onChange={handleFileUpload}
                className="hidden"
              />

              {!uploadedFile ? (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-border/60 rounded-xl p-8 text-center hover:border-primary/40 transition-colors cursor-pointer group"
                >
                  <Upload className="h-8 w-8 text-muted-foreground mx-auto mb-3 group-hover:text-primary transition-colors" />
                  <p className="text-sm font-medium text-foreground">Drop file here or click to upload</p>
                  <p className="text-xs text-muted-foreground mt-1.5">
                    {isImageProcessor ? "Supports: PNG, JPG, WEBP" : `Supports: ${tool.outputFormats.join(", ")}`}
                  </p>
                </div>
              ) : (
                <div className="bg-muted/50 rounded-xl p-4 border border-border/50">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {uploadPreview ? (
                        <img src={uploadPreview} alt="Preview" className="h-12 w-12 rounded-lg object-cover" />
                      ) : (
                        <div className="h-12 w-12 rounded-lg bg-muted flex items-center justify-center">
                          <FileText className="h-5 w-5 text-muted-foreground" />
                        </div>
                      )}
                      <div>
                        <p className="text-sm font-medium text-foreground truncate max-w-[200px]">{uploadedFile.name}</p>
                        <p className="text-xs text-muted-foreground">{(uploadedFile.size / 1024).toFixed(1)} KB</p>
                      </div>
                    </div>
                    <button onClick={handleRemoveFile} className="p-1.5 rounded-lg hover:bg-muted transition-colors">
                      <X className="h-4 w-4 text-muted-foreground" />
                    </button>
                  </div>

                  {loading && isImageProcessor && (
                    <div className="mt-2">
                      <div className="flex justify-between text-xs text-muted-foreground mb-1">
                        <span>Processing...</span>
                        <span>{bgProgress}%</span>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-brand rounded-full transition-all duration-300"
                          style={{ width: `${bgProgress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Advanced toggle */}
          {showTextInput && (
            <>
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 mt-3 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <Settings2 className="h-3.5 w-3.5" />
                Advanced Settings
                <ChevronDown className={`h-3 w-3 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
              </button>

              {showAdvanced && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="mt-3 p-4 bg-muted/30 rounded-xl space-y-3 border border-border/30"
                >
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Output Format</label>
                    <select
                      value={outputFormat}
                      onChange={(e) => setOutputFormat(e.target.value)}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                    >
                      {tool.outputFormats.map((f) => (
                        <option key={f} value={f}>{f}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Tone</label>
                    <select
                      value={tone}
                      onChange={(e) => setTone(e.target.value)}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                    >
                      {["Professional", "Casual", "Creative", "Academic", "Technical", "Friendly"].map((t) => (
                        <option key={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                </motion.div>
              )}
            </>
          )}

          <button
            onClick={handleGenerate}
            disabled={(showTextInput && !input.trim() && !uploadedFile) || (isImageProcessor && !uploadedFile) || loading}
            className="mt-4 w-full py-3 rounded-xl bg-gradient-brand text-primary-foreground font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {isImageProcessor ? "Processing..." : isImageGenTool ? "Generating Image..." : isVideoGenTool ? videoProgress || "Generating Video..." : "Generating..."}
              </>
            ) : (
              <>
                {isVideoGenTool ? <Film className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                {isImageProcessor ? "Remove Background" : isImageGenTool ? "Generate Image" : isVideoGenTool ? "Generate Video" : "Generate"}
                {showTextInput && <kbd className="hidden sm:inline text-xs opacity-60 ml-2">⌘↵</kbd>}
              </>
            )}
          </button>
        </motion.div>

        {/* Output Panel */}
        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-card rounded-2xl border border-border p-5 flex flex-col"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-foreground">Output</h2>
            {output && <span className="text-xs text-muted-foreground">{output.length} chars</span>}
          </div>

          {/* Image output */}
          {isImageProcessor ? (
            <div className="flex-1 min-h-[300px] max-h-[500px] bg-[repeating-conic-gradient(hsl(var(--muted))_0%_25%,transparent_0%_50%)] bg-[length:20px_20px] rounded-xl flex items-center justify-center border border-border/30 overflow-hidden">
              {processedImage ? (
                <img src={processedImage} alt="Background removed" className="max-w-full max-h-full object-contain" />
              ) : loading ? (
                <div className="flex flex-col items-center gap-3 text-muted-foreground">
                  <Loader2 className="h-8 w-8 animate-spin" />
                  <span className="text-sm">Removing background...</span>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 text-muted-foreground p-8">
                  <ImageIcon className="h-10 w-10 opacity-40" />
                  <span className="text-sm">Processed image will appear here</span>
                </div>
              )}
            </div>
          ) : isImageGenTool ? (
            <div className="flex-1 min-h-[300px] max-h-[500px] rounded-xl flex items-center justify-center border border-border/30 overflow-hidden bg-muted/30">
              {generatedImage ? (
                <img src={generatedImage} alt="AI Generated" className="max-w-full max-h-full object-contain" />
              ) : loading ? (
                <div className="flex flex-col items-center gap-4 text-muted-foreground">
                  <div className="relative">
                    <Loader2 className="h-10 w-10 animate-spin" />
                    <Sparkles className="h-4 w-4 absolute -top-1 -right-1 text-primary animate-pulse" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium">Generating your image...</p>
                    <p className="text-xs mt-1 opacity-70">This may take 10-30 seconds</p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 text-muted-foreground p-8">
                  <ImageIcon className="h-10 w-10 opacity-40" />
                  <span className="text-sm">Your AI-generated image will appear here</span>
                </div>
              )}
            </div>
          ) : isVideoGenTool ? (
            <div className="flex-1 min-h-[300px] max-h-[500px] rounded-xl flex flex-col border border-border/30 overflow-hidden bg-muted/30">
              {videoUrl ? (
                <video src={videoUrl} controls className="w-full h-full object-contain rounded-xl" />
              ) : loading ? (
                <div className="flex-1 flex flex-col items-center justify-center gap-4 p-6">
                  <div className="relative">
                    <Loader2 className="h-10 w-10 animate-spin text-primary" />
                    <Film className="h-4 w-4 absolute -top-1 -right-1 text-primary animate-pulse" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-foreground">{videoProgress || "Starting..."}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Step {videoStep}/4: {["", "Planning scenes", "Generating visuals", "Composing video", "Done"][videoStep]}
                    </p>
                  </div>
                  {/* Scene thumbnails as they generate */}
                  {videoScenes.length > 0 && (
                    <div className="w-full mt-4 space-y-2 max-h-[200px] overflow-y-auto">
                      {videoScenes.map((scene, i) => (
                        <div key={i} className="flex items-center gap-3 bg-background/50 rounded-lg p-2">
                          {scene.imageUrl ? (
                            <img src={scene.imageUrl} alt={scene.title} className="h-12 w-20 rounded object-cover" />
                          ) : (
                            <div className="h-12 w-20 rounded bg-muted flex items-center justify-center">
                              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-foreground truncate">Scene {scene.sceneNumber}: {scene.title}</p>
                            <p className="text-xs text-muted-foreground">{scene.durationSeconds}s</p>
                          </div>
                          {scene.imageUrl && <Check className="h-4 w-4 text-green-500 shrink-0" />}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center gap-2 text-muted-foreground p-8">
                  <Film className="h-10 w-10 opacity-40" />
                  <span className="text-sm">Your AI-generated video will appear here</span>
                  <span className="text-xs opacity-60">Enter a script, set duration, and click Generate</span>
                </div>
              )}
            </div>
          ) : (
            <div
              ref={outputRef}
              className="flex-1 min-h-[300px] max-h-[500px] overflow-y-auto bg-muted/30 rounded-xl p-4 text-sm text-foreground whitespace-pre-wrap font-mono leading-relaxed border border-border/30"
            >
              {loading && !output && (
                <div className="flex items-center gap-3 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>AI is thinking...</span>
                </div>
              )}
              {output || (!loading && (
                <span className="text-muted-foreground">
                  Output will appear here after generation...
                </span>
              ))}
              {loading && output && (
                <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-0.5" />
              )}
            </div>
          )}

          {/* Action bar */}
          <div className="flex flex-wrap gap-2 mt-4">
            {!isImageProcessor && (
              <button
                onClick={handleCopy}
                disabled={!output}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-muted text-sm font-medium text-foreground hover:bg-muted/80 disabled:opacity-40 transition-colors"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                {copied ? "Copied!" : "Copy"}
              </button>
            )}

            {/* Download dropdown */}
            <div className="relative group">
              <button
                disabled={!hasOutput}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-muted text-sm font-medium text-foreground hover:bg-muted/80 disabled:opacity-40 transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Download
                <ChevronDown className="h-3 w-3" />
              </button>
              <div className="absolute top-full left-0 mt-1 bg-card border border-border rounded-xl shadow-lg py-1 min-w-[140px] opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                {tool.outputFormats.map((f) => (
                  <button
                    key={f}
                    onClick={() => handleDownload(f)}
                    className="w-full text-left px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors flex items-center gap-2"
                  >
                    {getFormatIcon(f)}
                    <span>{f}</span>
                    {["PPTX", "PDF", "DOCX"].includes(f) && (
                      <span className="ml-auto text-[10px] text-primary font-medium">REAL</span>
                    )}
                  </button>
                ))}
                {!isImageProcessor && (
                  <button
                    onClick={() => handleDownload("TXT")}
                    className="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:bg-muted transition-colors flex items-center gap-2"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    Plain Text
                  </button>
                )}
              </div>
            </div>

            {!isImageProcessor && (
              <button
                onClick={handleSendToTool}
                disabled={!output}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-muted text-sm font-medium text-foreground hover:bg-muted/80 disabled:opacity-40 transition-colors"
              >
                <Send className="h-3.5 w-3.5" />
                Chain
              </button>
            )}

            <button
              onClick={() => { setOutput(""); setInput(""); handleRemoveFile(); setProcessedImage(null); setGeneratedImage(null); setVideoUrl(null); setVideoScenes([]); setVideoStep(0); setVideoProgress(""); }}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-muted text-sm font-medium text-muted-foreground hover:bg-muted/80 transition-colors ml-auto"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Clear
            </button>
          </div>
        </motion.div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-2 mt-4">
        {tool.tags.map((tag) => (
          <span key={tag} className="px-2.5 py-1 rounded-lg bg-muted text-xs text-muted-foreground">#{tag}</span>
        ))}
      </div>
    </div>
  );
};

function getPlaceholder(toolId: string): string {
  const placeholders: Record<string, string> = {
    "article-writer": "Write an article about the future of artificial intelligence in healthcare...",
    "email-composer": "Write a professional follow-up email after a job interview at Google...",
    "summarizer": "Paste your text here to get a concise summary...",
    "code-gen": "Create a React component for a responsive navigation menu with dropdown submenus...",
    "code-debug": "Paste your buggy code here and describe the issue...",
    "image-gen": "A cyberpunk cityscape at sunset with neon signs and flying cars...",
    "logo-maker": "A modern minimalist logo for a tech startup called 'NovaTech'...",
    "pitch-deck": "Create a pitch deck for an AI-powered fitness coaching app targeting millennials. Include problem, solution, market size, business model, and ask...",
    "resume-builder": "Senior Software Engineer with 8 years experience in React, Node.js, and AWS...",
    "translator": "Translate to Spanish: 'The future belongs to those who believe in the beauty of their dreams.'",
    "social-post": "Write a LinkedIn post about launching a new product - a project management tool for remote teams...",
    "math-solver": "Solve: If f(x) = 3x² + 2x - 5, find f'(x) and determine where f(x) has a minimum...",
    "invoice-gen": "Create an invoice for Web Development services: 40 hours at $150/hr, domain hosting $200, SSL certificate $100. Client: Acme Corp...",
    "contract-gen": "Draft a freelance software development contract between John Doe (developer) and Acme Corp (client) for 3 months...",
    "business-plan": "Write a business plan for a sustainable fashion e-commerce platform targeting Gen Z consumers...",
    "video-gen": "Write your video script here. Example: A documentary about the rise of artificial intelligence...",
  };
  return placeholders[toolId] || `Describe what you want to ${toolId.replace(/-/g, " ")}...`;
}

function getFormatIcon(format: string) {
  switch (format) {
    case "HTML": return <Globe className="h-3.5 w-3.5" />;
    case "PPTX": return <FileText className="h-3.5 w-3.5 text-orange-400" />;
    case "PDF": return <FileText className="h-3.5 w-3.5 text-red-400" />;
    case "DOCX": return <FileText className="h-3.5 w-3.5 text-blue-400" />;
    case "PNG":
    case "JPG":
    case "WEBP": return <ImageIcon className="h-3.5 w-3.5 text-purple-400" />;
    case "JSON":
    case "CSS":
    case "CSV": return <FileCode className="h-3.5 w-3.5" />;
    case "WEBM":
    case "MP4": return <Film className="h-3.5 w-3.5 text-rose-400" />;
    default: return <FileText className="h-3.5 w-3.5" />;
  }
}

export default ToolPage;
