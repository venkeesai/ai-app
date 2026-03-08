import {
  FileText, Image, Code, Video, Music, Globe, BarChart3, Presentation, Mail,
  Palette, Type, Wand2, BookOpen, Calculator, Languages, MessageSquare, Mic,
  Camera, Scissors, Layers, Zap, Brain, Lightbulb, PenTool, FileSpreadsheet,
  Database, Lock, Search, Hash, QrCode, Smartphone, Printer, CloudUpload,
  Megaphone, TrendingUp, Users, Briefcase, GraduationCap, Heart, Shield,
  Clock, Map, Gift, Star, Sparkles, Bot, Workflow, Terminal, Binary,
  Cpu, Network, HardDrive, Headphones, Radio, Film, Clapperboard,
  ImagePlus, FileImage, FileVideo, FileAudio, FilePlus, FileCheck,
  LayoutGrid, PaintBucket, Brush, Eraser, Crop, RotateCcw,
  AlignLeft, AlignCenter, List, Table, PieChart, LineChart,
  Share2, Link, Download, Upload, Send, Archive,
  Eye, Glasses, Scan, Fingerprint, Key, Ruler,
  Compass, Navigation, Bookmark, Tag, Flag, Bell,
  Coffee, Flame, Rocket, Target, Award, Crown,
  Smile, Frown, ThumbsUp, AlertTriangle, Info, HelpCircle,
} from "lucide-react";

export type ToolCategory =
  | "writing"
  | "image"
  | "code"
  | "video"
  | "audio"
  | "data"
  | "business"
  | "education"
  | "social"
  | "productivity"
  | "design"
  | "conversion";

export interface Tool {
  id: string;
  name: string;
  description: string;
  category: ToolCategory;
  icon: any;
  trending?: boolean;
  inputType: "text" | "file" | "both";
  outputFormats: string[];
  tags: string[];
}

export const categories: { id: ToolCategory; name: string; icon: any; color: string }[] = [
  { id: "writing", name: "Writing & Text", icon: Type, color: "195 100% 50%" },
  { id: "image", name: "Image & Design", icon: Image, color: "260 70% 65%" },
  { id: "code", name: "Code & Dev", icon: Code, color: "150 80% 45%" },
  { id: "video", name: "Video & Film", icon: Video, color: "340 80% 55%" },
  { id: "audio", name: "Audio & Music", icon: Music, color: "30 90% 55%" },
  { id: "data", name: "Data & Analytics", icon: BarChart3, color: "200 80% 55%" },
  { id: "business", name: "Business", icon: Briefcase, color: "220 70% 55%" },
  { id: "education", name: "Education", icon: GraduationCap, color: "170 70% 45%" },
  { id: "social", name: "Social Media", icon: Share2, color: "290 70% 55%" },
  { id: "productivity", name: "Productivity", icon: Zap, color: "45 90% 50%" },
  { id: "design", name: "Design Tools", icon: Palette, color: "310 70% 55%" },
  { id: "conversion", name: "File Conversion", icon: RotateCcw, color: "180 60% 45%" },
];

export const tools: Tool[] = [
  // Writing & Text (15)
  { id: "article-writer", name: "Article Writer", description: "Generate long-form articles on any topic", category: "writing", icon: FileText, trending: true, inputType: "text", outputFormats: ["DOCX", "PDF", "TXT"], tags: ["blog", "content", "seo"] },
  { id: "email-composer", name: "Email Composer", description: "Craft professional emails instantly", category: "writing", icon: Mail, inputType: "text", outputFormats: ["TXT", "HTML"], tags: ["email", "business"] },
  { id: "summarizer", name: "Text Summarizer", description: "Summarize any document or article", category: "writing", icon: AlignCenter, trending: true, inputType: "both", outputFormats: ["TXT", "PDF"], tags: ["summary", "digest"] },
  { id: "paraphraser", name: "Paraphraser", description: "Rewrite content in different styles", category: "writing", icon: RotateCcw, inputType: "text", outputFormats: ["TXT"], tags: ["rewrite", "style"] },
  { id: "grammar-checker", name: "Grammar Checker", description: "Fix grammar, spelling, and style", category: "writing", icon: FileCheck, inputType: "text", outputFormats: ["TXT"], tags: ["grammar", "proofread"] },
  { id: "translator", name: "AI Translator", description: "Translate text to 100+ languages", category: "writing", icon: Languages, trending: true, inputType: "text", outputFormats: ["TXT", "DOCX"], tags: ["translate", "language"] },
  { id: "headline-gen", name: "Headline Generator", description: "Generate catchy headlines and titles", category: "writing", icon: Sparkles, inputType: "text", outputFormats: ["TXT"], tags: ["headline", "title"] },
  { id: "story-writer", name: "Story Writer", description: "Create creative stories and narratives", category: "writing", icon: BookOpen, inputType: "text", outputFormats: ["TXT", "PDF"], tags: ["story", "creative"] },
  { id: "poem-gen", name: "Poem Generator", description: "Write poems in any style", category: "writing", icon: PenTool, inputType: "text", outputFormats: ["TXT"], tags: ["poem", "poetry"] },
  { id: "script-writer", name: "Script Writer", description: "Write scripts for videos and podcasts", category: "writing", icon: Clapperboard, inputType: "text", outputFormats: ["TXT", "PDF"], tags: ["script", "video"] },
  { id: "resume-builder", name: "Resume Builder", description: "Create professional resumes", category: "writing", icon: FileText, trending: true, inputType: "text", outputFormats: ["PDF", "DOCX"], tags: ["resume", "cv"] },
  { id: "cover-letter", name: "Cover Letter", description: "Generate tailored cover letters", category: "writing", icon: Mail, inputType: "text", outputFormats: ["PDF", "DOCX"], tags: ["cover letter", "job"] },
  { id: "product-desc", name: "Product Description", description: "Write compelling product descriptions", category: "writing", icon: Tag, inputType: "text", outputFormats: ["TXT"], tags: ["product", "ecommerce"] },
  { id: "seo-writer", name: "SEO Content Writer", description: "Create SEO-optimized content", category: "writing", icon: Search, inputType: "text", outputFormats: ["TXT", "HTML"], tags: ["seo", "content"] },
  { id: "speech-writer", name: "Speech Writer", description: "Compose speeches for any occasion", category: "writing", icon: Mic, inputType: "text", outputFormats: ["TXT", "PDF"], tags: ["speech", "presentation"] },

  // Image & Design (15)
  { id: "image-gen", name: "Image Generator", description: "Create images from text descriptions", category: "image", icon: ImagePlus, trending: true, inputType: "text", outputFormats: ["PNG", "JPG", "WEBP"], tags: ["generate", "ai art"] },
  { id: "logo-maker", name: "Logo Maker", description: "Design professional logos instantly", category: "image", icon: Palette, trending: true, inputType: "text", outputFormats: ["PNG", "SVG"], tags: ["logo", "brand"] },
  { id: "bg-remover", name: "Background Remover", description: "Remove backgrounds from images", category: "image", icon: Eraser, trending: true, inputType: "file", outputFormats: ["PNG"], tags: ["background", "cutout"] },
  { id: "image-upscaler", name: "Image Upscaler", description: "Enhance image resolution with AI", category: "image", icon: Crop, inputType: "file", outputFormats: ["PNG", "JPG"], tags: ["upscale", "enhance"] },
  { id: "color-palette", name: "Color Palette Gen", description: "Generate color palettes from concepts", category: "image", icon: PaintBucket, inputType: "text", outputFormats: ["PNG", "JSON"], tags: ["color", "palette"] },
  { id: "icon-gen", name: "Icon Generator", description: "Create custom icons and symbols", category: "image", icon: Layers, inputType: "text", outputFormats: ["SVG", "PNG"], tags: ["icon", "symbol"] },
  { id: "mockup-gen", name: "Mockup Generator", description: "Create product mockups", category: "image", icon: Smartphone, inputType: "file", outputFormats: ["PNG", "JPG"], tags: ["mockup", "product"] },
  { id: "image-to-text", name: "Image to Text (OCR)", description: "Extract text from images", category: "image", icon: Eye, inputType: "file", outputFormats: ["TXT"], tags: ["ocr", "extract"] },
  { id: "face-enhancer", name: "Face Enhancer", description: "Enhance facial features in photos", category: "image", icon: Smile, inputType: "file", outputFormats: ["PNG", "JPG"], tags: ["face", "enhance"] },
  { id: "art-style", name: "Art Style Transfer", description: "Apply artistic styles to photos", category: "image", icon: Brush, inputType: "file", outputFormats: ["PNG", "JPG"], tags: ["art", "style"] },
  { id: "meme-gen", name: "Meme Generator", description: "Create memes with AI captions", category: "image", icon: Smile, inputType: "both", outputFormats: ["PNG", "JPG"], tags: ["meme", "fun"] },
  { id: "infographic", name: "Infographic Maker", description: "Design data-driven infographics", category: "image", icon: BarChart3, inputType: "text", outputFormats: ["PNG", "PDF"], tags: ["infographic", "data"] },
  { id: "banner-maker", name: "Banner Maker", description: "Create web and social banners", category: "image", icon: LayoutGrid, inputType: "text", outputFormats: ["PNG", "JPG"], tags: ["banner", "social"] },
  { id: "avatar-gen", name: "Avatar Generator", description: "Create unique AI avatars", category: "image", icon: Users, inputType: "both", outputFormats: ["PNG"], tags: ["avatar", "profile"] },
  { id: "qr-gen", name: "QR Code Generator", description: "Generate styled QR codes", category: "image", icon: QrCode, inputType: "text", outputFormats: ["PNG", "SVG"], tags: ["qr", "code"] },

  // Code & Dev (12)
  { id: "code-gen", name: "Code Generator", description: "Generate code in any language", category: "code", icon: Code, trending: true, inputType: "text", outputFormats: ["TXT"], tags: ["code", "programming"] },
  { id: "code-debug", name: "Code Debugger", description: "Find and fix bugs in your code", category: "code", icon: AlertTriangle, inputType: "text", outputFormats: ["TXT"], tags: ["debug", "fix"] },
  { id: "code-explain", name: "Code Explainer", description: "Understand any code snippet", category: "code", icon: Info, inputType: "text", outputFormats: ["TXT"], tags: ["explain", "learn"] },
  { id: "code-convert", name: "Code Converter", description: "Convert code between languages", category: "code", icon: RotateCcw, inputType: "text", outputFormats: ["TXT"], tags: ["convert", "language"] },
  { id: "regex-gen", name: "Regex Generator", description: "Build regex patterns from descriptions", category: "code", icon: Hash, inputType: "text", outputFormats: ["TXT"], tags: ["regex", "pattern"] },
  { id: "sql-gen", name: "SQL Generator", description: "Generate SQL queries from natural language", category: "code", icon: Database, inputType: "text", outputFormats: ["TXT"], tags: ["sql", "database"] },
  { id: "api-doc", name: "API Doc Generator", description: "Create API documentation", category: "code", icon: FileText, inputType: "text", outputFormats: ["MD", "HTML"], tags: ["api", "docs"] },
  { id: "json-tool", name: "JSON Formatter", description: "Format, validate, and transform JSON", category: "code", icon: Binary, inputType: "text", outputFormats: ["JSON"], tags: ["json", "format"] },
  { id: "html-gen", name: "HTML Generator", description: "Generate HTML from descriptions", category: "code", icon: Globe, inputType: "text", outputFormats: ["HTML"], tags: ["html", "web"] },
  { id: "css-gen", name: "CSS Generator", description: "Generate CSS styles and animations", category: "code", icon: PaintBucket, inputType: "text", outputFormats: ["CSS"], tags: ["css", "style"] },
  { id: "terminal-cmd", name: "Terminal Commands", description: "Get terminal commands for any task", category: "code", icon: Terminal, inputType: "text", outputFormats: ["TXT"], tags: ["terminal", "command"] },
  { id: "git-helper", name: "Git Helper", description: "Generate git commands and messages", category: "code", icon: Network, inputType: "text", outputFormats: ["TXT"], tags: ["git", "version control"] },

  // Video (9)
  { id: "video-gen", name: "AI Video Generator", description: "Generate real videos from scripts with AI scenes", category: "video", icon: Film, trending: true, inputType: "text", outputFormats: ["WEBM", "MP4"], tags: ["video", "generate", "scenes", "ai"] },
  { id: "video-script", name: "Video Script Gen", description: "Write scripts for YouTube and TikTok", category: "video", icon: Film, inputType: "text", outputFormats: ["TXT", "PDF"], tags: ["script", "youtube"] },
  { id: "subtitle-gen", name: "Subtitle Generator", description: "Generate subtitles from video", category: "video", icon: FileText, inputType: "file", outputFormats: ["SRT", "VTT"], tags: ["subtitle", "caption"] },
  { id: "thumbnail-maker", name: "Thumbnail Maker", description: "Create eye-catching thumbnails", category: "video", icon: Camera, inputType: "text", outputFormats: ["PNG", "JPG"], tags: ["thumbnail", "youtube"] },
  { id: "storyboard", name: "Storyboard Creator", description: "Create visual storyboards", category: "video", icon: LayoutGrid, inputType: "text", outputFormats: ["PNG", "PDF"], tags: ["storyboard", "plan"] },
  { id: "video-idea", name: "Video Idea Generator", description: "Get trending video ideas", category: "video", icon: Lightbulb, inputType: "text", outputFormats: ["TXT"], tags: ["idea", "content"] },
  { id: "video-hook", name: "Hook Generator", description: "Create engaging video hooks", category: "video", icon: Zap, inputType: "text", outputFormats: ["TXT"], tags: ["hook", "engagement"] },
  { id: "scene-desc", name: "Scene Descriptor", description: "Describe scenes for video production", category: "video", icon: Eye, inputType: "text", outputFormats: ["TXT"], tags: ["scene", "direction"] },
  { id: "video-outline", name: "Video Outline", description: "Create structured video outlines", category: "video", icon: List, inputType: "text", outputFormats: ["TXT", "PDF"], tags: ["outline", "structure"] },

  // Audio (8)
  { id: "text-to-speech", name: "Text to Speech", description: "Convert text to natural speech", category: "audio", icon: Headphones, trending: true, inputType: "text", outputFormats: ["MP3", "WAV"], tags: ["tts", "voice"] },
  { id: "speech-to-text", name: "Speech to Text", description: "Transcribe audio to text", category: "audio", icon: Mic, inputType: "file", outputFormats: ["TXT", "SRT"], tags: ["transcribe", "stt"] },
  { id: "podcast-script", name: "Podcast Script", description: "Write engaging podcast scripts", category: "audio", icon: Radio, inputType: "text", outputFormats: ["TXT", "PDF"], tags: ["podcast", "script"] },
  { id: "music-gen", name: "Music Generator", description: "Create background music", category: "audio", icon: Music, inputType: "text", outputFormats: ["MP3"], tags: ["music", "background"] },
  { id: "voice-clone", name: "Voice Cloner", description: "Clone and modify voices", category: "audio", icon: Mic, inputType: "file", outputFormats: ["MP3", "WAV"], tags: ["voice", "clone"] },
  { id: "audio-enhance", name: "Audio Enhancer", description: "Improve audio quality", category: "audio", icon: Wand2, inputType: "file", outputFormats: ["MP3", "WAV"], tags: ["enhance", "quality"] },
  { id: "sound-fx", name: "Sound FX Generator", description: "Create custom sound effects", category: "audio", icon: Sparkles, inputType: "text", outputFormats: ["MP3", "WAV"], tags: ["sfx", "sound"] },
  { id: "audio-to-text-summary", name: "Audio Summarizer", description: "Summarize long audio recordings", category: "audio", icon: FileText, inputType: "file", outputFormats: ["TXT"], tags: ["summarize", "audio"] },

  // Data & Analytics (8)
  { id: "data-viz", name: "Data Visualizer", description: "Create charts from your data", category: "data", icon: PieChart, trending: true, inputType: "both", outputFormats: ["PNG", "SVG"], tags: ["chart", "visualization"] },
  { id: "csv-analyzer", name: "CSV Analyzer", description: "Analyze and query CSV files", category: "data", icon: FileSpreadsheet, inputType: "file", outputFormats: ["TXT", "CSV"], tags: ["csv", "analyze"] },
  { id: "survey-maker", name: "Survey Creator", description: "Create surveys and questionnaires", category: "data", icon: List, inputType: "text", outputFormats: ["JSON", "PDF"], tags: ["survey", "form"] },
  { id: "report-gen", name: "Report Generator", description: "Generate analytical reports", category: "data", icon: FileText, inputType: "both", outputFormats: ["PDF", "DOCX"], tags: ["report", "analysis"] },
  { id: "trend-analyzer", name: "Trend Analyzer", description: "Analyze market and data trends", category: "data", icon: TrendingUp, inputType: "text", outputFormats: ["TXT", "PNG"], tags: ["trend", "market"] },
  { id: "stats-calc", name: "Statistics Calculator", description: "Perform statistical calculations", category: "data", icon: Calculator, inputType: "text", outputFormats: ["TXT"], tags: ["statistics", "math"] },
  { id: "json-to-csv", name: "JSON to CSV", description: "Convert JSON to CSV format", category: "data", icon: Table, inputType: "file", outputFormats: ["CSV"], tags: ["convert", "data"] },
  { id: "data-cleaner", name: "Data Cleaner", description: "Clean and normalize datasets", category: "data", icon: Wand2, inputType: "file", outputFormats: ["CSV", "JSON"], tags: ["clean", "normalize"] },

  // Business (10)
  { id: "pitch-deck", name: "Pitch Deck Creator", description: "Generate investor pitch decks", category: "business", icon: Presentation, trending: true, inputType: "text", outputFormats: ["PDF", "PPTX"], tags: ["pitch", "investor"] },
  { id: "business-plan", name: "Business Plan Writer", description: "Create comprehensive business plans", category: "business", icon: Briefcase, inputType: "text", outputFormats: ["PDF", "DOCX"], tags: ["plan", "strategy"] },
  { id: "invoice-gen", name: "Invoice Generator", description: "Create professional invoices", category: "business", icon: FileText, inputType: "text", outputFormats: ["PDF"], tags: ["invoice", "billing"] },
  { id: "contract-gen", name: "Contract Generator", description: "Draft legal contracts", category: "business", icon: Shield, inputType: "text", outputFormats: ["PDF", "DOCX"], tags: ["contract", "legal"] },
  { id: "swot-analysis", name: "SWOT Analysis", description: "Generate SWOT analyses", category: "business", icon: Target, inputType: "text", outputFormats: ["PDF", "TXT"], tags: ["swot", "analysis"] },
  { id: "marketing-copy", name: "Marketing Copy", description: "Write marketing and ad copy", category: "business", icon: Megaphone, inputType: "text", outputFormats: ["TXT"], tags: ["marketing", "advertising"] },
  { id: "brand-name", name: "Brand Name Generator", description: "Generate unique brand names", category: "business", icon: Crown, inputType: "text", outputFormats: ["TXT"], tags: ["brand", "naming"] },
  { id: "meeting-notes", name: "Meeting Notes", description: "Generate structured meeting notes", category: "business", icon: FileCheck, inputType: "text", outputFormats: ["TXT", "PDF"], tags: ["meeting", "notes"] },
  { id: "proposal-writer", name: "Proposal Writer", description: "Write business proposals", category: "business", icon: Send, inputType: "text", outputFormats: ["PDF", "DOCX"], tags: ["proposal", "business"] },
  { id: "competitor-analysis", name: "Competitor Analysis", description: "Analyze competitors in your market", category: "business", icon: Eye, inputType: "text", outputFormats: ["PDF", "TXT"], tags: ["competitor", "market"] },

  // Education (9)
  { id: "flashcard-gen", name: "Flashcard Generator", description: "Create study flashcards", category: "education", icon: Layers, inputType: "text", outputFormats: ["PDF", "JSON"], tags: ["flashcard", "study"] },
  { id: "quiz-maker", name: "Quiz Maker", description: "Generate quizzes on any topic", category: "education", icon: HelpCircle, inputType: "text", outputFormats: ["PDF", "JSON"], tags: ["quiz", "test"] },
  { id: "lesson-plan", name: "Lesson Planner", description: "Create detailed lesson plans", category: "education", icon: BookOpen, inputType: "text", outputFormats: ["PDF", "DOCX"], tags: ["lesson", "teaching"] },
  { id: "essay-helper", name: "Essay Assistant", description: "Help structure and write essays", category: "education", icon: PenTool, inputType: "text", outputFormats: ["TXT", "DOCX"], tags: ["essay", "academic"] },
  { id: "math-solver", name: "Math Solver", description: "Solve math problems step by step", category: "education", icon: Calculator, inputType: "text", outputFormats: ["TXT"], tags: ["math", "solve"] },
  { id: "answer-key-generator", name: "Answer Key Generator", description: "Upload a question paper and generate a complete structured answer key in one final response", category: "education", icon: FileCheck, trending: true, inputType: "file", outputFormats: ["TXT", "PDF", "DOCX"], tags: ["answer key", "exam", "question paper"] },
  { id: "study-guide", name: "Study Guide Creator", description: "Generate comprehensive study guides", category: "education", icon: GraduationCap, inputType: "text", outputFormats: ["PDF"], tags: ["study", "guide"] },
  { id: "citation-gen", name: "Citation Generator", description: "Generate citations in any format", category: "education", icon: BookOpen, inputType: "text", outputFormats: ["TXT"], tags: ["citation", "reference"] },
  { id: "explain-like-5", name: "Explain Like I'm 5", description: "Simplify complex concepts", category: "education", icon: Lightbulb, inputType: "text", outputFormats: ["TXT"], tags: ["explain", "simplify"] },

  // Social Media (8)
  { id: "social-post", name: "Social Post Writer", description: "Create viral social media posts", category: "social", icon: MessageSquare, trending: true, inputType: "text", outputFormats: ["TXT"], tags: ["social", "post"] },
  { id: "hashtag-gen", name: "Hashtag Generator", description: "Generate relevant hashtags", category: "social", icon: Hash, inputType: "text", outputFormats: ["TXT"], tags: ["hashtag", "social"] },
  { id: "bio-writer", name: "Bio Writer", description: "Write compelling social media bios", category: "social", icon: Users, inputType: "text", outputFormats: ["TXT"], tags: ["bio", "profile"] },
  { id: "caption-gen", name: "Caption Generator", description: "Create engaging photo captions", category: "social", icon: Camera, inputType: "both", outputFormats: ["TXT"], tags: ["caption", "instagram"] },
  { id: "thread-writer", name: "Thread Writer", description: "Create engaging Twitter/X threads", category: "social", icon: List, inputType: "text", outputFormats: ["TXT"], tags: ["thread", "twitter"] },
  { id: "content-calendar", name: "Content Calendar", description: "Plan your content schedule", category: "social", icon: Clock, inputType: "text", outputFormats: ["CSV", "PDF"], tags: ["calendar", "plan"] },
  { id: "influencer-brief", name: "Influencer Brief", description: "Create influencer collaboration briefs", category: "social", icon: Star, inputType: "text", outputFormats: ["PDF"], tags: ["influencer", "brief"] },
  { id: "ad-copy", name: "Ad Copy Generator", description: "Write ad copy for all platforms", category: "social", icon: Megaphone, inputType: "text", outputFormats: ["TXT"], tags: ["ads", "copy"] },

  // Productivity (8)
  { id: "todo-gen", name: "Task Planner", description: "Create structured task lists", category: "productivity", icon: List, inputType: "text", outputFormats: ["TXT", "JSON"], tags: ["task", "plan"] },
  { id: "mind-map", name: "Mind Map Generator", description: "Create visual mind maps", category: "productivity", icon: Network, inputType: "text", outputFormats: ["PNG", "JSON"], tags: ["mindmap", "brainstorm"] },
  { id: "decision-maker", name: "Decision Maker", description: "AI-powered decision analysis", category: "productivity", icon: Compass, inputType: "text", outputFormats: ["TXT"], tags: ["decision", "analysis"] },
  { id: "habit-tracker", name: "Habit Tracker Setup", description: "Design personalized habit trackers", category: "productivity", icon: Target, inputType: "text", outputFormats: ["PDF"], tags: ["habit", "tracking"] },
  { id: "time-blocker", name: "Time Block Planner", description: "Create time-blocked schedules", category: "productivity", icon: Clock, inputType: "text", outputFormats: ["PDF", "TXT"], tags: ["schedule", "time"] },
  { id: "goal-setter", name: "Goal Setting Assistant", description: "Set and structure SMART goals", category: "productivity", icon: Flag, inputType: "text", outputFormats: ["TXT", "PDF"], tags: ["goals", "smart"] },
  { id: "priority-matrix", name: "Priority Matrix", description: "Prioritize tasks with Eisenhower matrix", category: "productivity", icon: LayoutGrid, inputType: "text", outputFormats: ["PNG", "PDF"], tags: ["priority", "matrix"] },
  { id: "daily-planner", name: "Daily Planner", description: "Generate daily schedules", category: "productivity", icon: Clock, inputType: "text", outputFormats: ["PDF"], tags: ["daily", "planner"] },

  // File Conversion (8)
  { id: "pdf-to-word", name: "PDF to Word", description: "Convert PDF files to DOCX", category: "conversion", icon: FileText, inputType: "file", outputFormats: ["DOCX"], tags: ["pdf", "word"] },
  { id: "word-to-pdf", name: "Word to PDF", description: "Convert DOCX to PDF", category: "conversion", icon: FileText, inputType: "file", outputFormats: ["PDF"], tags: ["word", "pdf"] },
  { id: "image-converter", name: "Image Converter", description: "Convert between image formats", category: "conversion", icon: FileImage, inputType: "file", outputFormats: ["PNG", "JPG", "WEBP", "SVG"], tags: ["image", "convert"] },
  { id: "audio-converter", name: "Audio Converter", description: "Convert between audio formats", category: "conversion", icon: FileAudio, inputType: "file", outputFormats: ["MP3", "WAV", "OGG"], tags: ["audio", "convert"] },
  { id: "video-converter", name: "Video Converter", description: "Convert between video formats", category: "conversion", icon: FileVideo, inputType: "file", outputFormats: ["MP4", "WEBM", "AVI"], tags: ["video", "convert"] },
  { id: "md-to-html", name: "Markdown to HTML", description: "Convert Markdown to HTML", category: "conversion", icon: Code, inputType: "text", outputFormats: ["HTML"], tags: ["markdown", "html"] },
  { id: "csv-to-json", name: "CSV to JSON", description: "Convert CSV to JSON format", category: "conversion", icon: Table, inputType: "file", outputFormats: ["JSON"], tags: ["csv", "json"] },
  { id: "text-to-pdf", name: "Text to PDF", description: "Convert plain text to PDF", category: "conversion", icon: FilePlus, inputType: "text", outputFormats: ["PDF"], tags: ["text", "pdf"] },
];

export const getToolsByCategory = (category: ToolCategory) =>
  tools.filter((t) => t.category === category);

export const getTrendingTools = () => tools.filter((t) => t.trending);

export const searchTools = (query: string) => {
  const q = query.toLowerCase();
  return tools.filter(
    (t) =>
      t.name.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q) ||
      t.tags.some((tag) => tag.includes(q)) ||
      t.category.includes(q)
  );
};
