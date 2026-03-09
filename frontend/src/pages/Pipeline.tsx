import { useCallback, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle,
  ChevronDown,
  Circle,
  File,
  FileText,
  Image,
  Loader2,
  Mail,
  Paperclip,
  Play,
  RotateCcw,
  Sparkles,
  Scale,
  Upload,
  UserCheck,
  XCircle,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type {
  ContentExtractionResult,
  Document,
  ExtractedTrade,
  FieldComparison,
  PipelineStepKey,
  PipelineStepStatus,
  ValidationResult,
} from '@/types/trade';

const API_BASE = 'http://localhost:8000';

const STEPS: { key: PipelineStepKey; label: string; icon: React.ReactNode }[] = [
  { key: 'upload', label: 'Inbound Evidence', icon: <Upload className="h-4 w-4" /> },
  { key: 'content_extraction', label: 'Content Extraction', icon: <FileText className="h-4 w-4" /> },
  { key: 'entity_extraction', label: 'Entity Extraction', icon: <Sparkles className="h-4 w-4" /> },
  { key: 'comparison', label: 'Trade Comparison', icon: <Scale className="h-4 w-4" /> },
  { key: 'review', label: 'Human Review', icon: <UserCheck className="h-4 w-4" /> },
];

const INITIAL_STEP_STATUSES: Record<PipelineStepKey, PipelineStepStatus> = {
  upload: 'pending',
  content_extraction: 'pending',
  entity_extraction: 'pending',
  comparison: 'pending',
  review: 'pending',
};

export function Pipeline() {
  // Pipeline state
  const [stepStatuses, setStepStatuses] = useState<Record<PipelineStepKey, PipelineStepStatus>>({ ...INITIAL_STEP_STATUSES });
  const [expandedSteps, setExpandedSteps] = useState<Set<PipelineStepKey>>(new Set(['upload']));
  const [isRunning, setIsRunning] = useState(false);

  // Data state for each step
  const [document, setDocument] = useState<Document | null>(null);
  const [contentExtraction, setContentExtraction] = useState<ContentExtractionResult | null>(null);
  const [extractedTrade, setExtractedTrade] = useState<ExtractedTrade | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);

  // LLM streaming progress state
  const [llmStatus, setLlmStatus] = useState('');
  const [llmProgress, setLlmProgress] = useState('');
  const [llmLog, setLlmLog] = useState<string[]>([]);

  // Upload state
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [textInput, setTextInput] = useState('');

  // Checker state
  const [checkerComment, setCheckerComment] = useState('');
  const [overrideStatus, setOverrideStatus] = useState<'MATCH' | 'PARTIAL' | 'MISMATCH'>('MATCH');
  const [overrideTradeId, setOverrideTradeId] = useState('');
  const [checkerSubmitted, setCheckerSubmitted] = useState(false);

  // Step error messages
  const [stepErrors, setStepErrors] = useState<Record<string, string>>({});

  const stepRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // -- Helpers --

  const updateStepStatus = (step: PipelineStepKey, status: PipelineStepStatus) => {
    setStepStatuses((prev) => ({ ...prev, [step]: status }));
  };

  const toggleStep = (step: PipelineStepKey) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(step)) {
        next.delete(step);
      } else {
        next.add(step);
      }
      return next;
    });
  };

  const expandStep = (step: PipelineStepKey, scroll: boolean = true) => {
    setExpandedSteps((prev) => new Set(prev).add(step));
    if (scroll) {
      setTimeout(() => {
        stepRefs.current[step]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 100);
    }
  };

  const resetPipeline = () => {
    setStepStatuses({ ...INITIAL_STEP_STATUSES });
    setExpandedSteps(new Set(['upload']));
    setIsRunning(false);
    setDocument(null);
    setContentExtraction(null);
    setExtractedTrade(null);
    setValidationResult(null);
    setTextInput('');
    setCheckerComment('');
    setOverrideTradeId('');
    setCheckerSubmitted(false);
    setStepErrors({});
    setLlmStatus('');
    setLlmProgress('');
    setLlmLog([]);
  };

  // -- Upload handlers --

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await uploadFile(files[0]);
    }
  }, []);

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await uploadFile(e.target.files[0]);
    }
  }, []);

  const uploadFile = async (file: globalThis.File) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Upload failed');
      }

      const doc: Document = await response.json();
      setDocument(doc);
      updateStepStatus('upload', 'complete');
      expandStep('upload');
    } catch (error) {
      console.error('Upload failed:', error);
      updateStepStatus('upload', 'error');
      setStepErrors((prev) => ({ ...prev, upload: String(error) }));
    }
    setIsUploading(false);
  };

  const handleTextSubmit = async () => {
    if (!textInput.trim()) return;
    setIsUploading(true);

    try {
      const response = await fetch(`${API_BASE}/api/documents/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: textInput }),
      });

      if (!response.ok) throw new Error('Text submission failed');

      const doc: Document = await response.json();
      setDocument(doc);
      updateStepStatus('upload', 'complete');
      expandStep('upload');
    } catch (error) {
      console.error('Text submission failed:', error);
      updateStepStatus('upload', 'error');
      setStepErrors((prev) => ({ ...prev, upload: String(error) }));
    }
    setIsUploading(false);
  };

  // -- Pipeline execution --

  const runPipeline = async () => {
    if (!document) return;
    setIsRunning(true);
    const docId = document.id;

    // Step 2: Content Extraction
    updateStepStatus('content_extraction', 'processing');
    expandStep('content_extraction');
    try {
      const response = await fetch(`${API_BASE}/api/documents/${docId}/content-extract`, { method: 'POST' });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Content extraction failed');
      }
      const updatedDoc: Document = await response.json();
      setDocument(updatedDoc);
      if (updatedDoc.content_extraction) {
        setContentExtraction(updatedDoc.content_extraction);
      }
      updateStepStatus('content_extraction', 'complete');
    } catch (error) {
      updateStepStatus('content_extraction', 'error');
      setStepErrors((prev) => ({ ...prev, content_extraction: String(error) }));
      setIsRunning(false);
      return;
    }

    // Step 3: Entity Extraction (with SSE streaming progress)
    updateStepStatus('entity_extraction', 'processing');
    expandStep('entity_extraction');
    setLlmStatus('Starting LLM extraction...');
    setLlmProgress('');
    setLlmLog([]);
    try {
      const extractionResult = await new Promise<Document>((resolve, reject) => {
        fetch(`${API_BASE}/api/documents/${docId}/extract-stream`, { method: 'POST' })
          .then(async (response) => {
            if (!response.ok) {
              const err = await response.json();
              reject(new Error(err.detail || 'Entity extraction failed'));
              return;
            }

            const reader = response.body?.getReader();
            if (!reader) {
              reject(new Error('No response stream'));
              return;
            }

            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n');
              buffer = lines.pop() || '';

              for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                  const event = JSON.parse(line.slice(6));

                  if (event.type === 'status') {
                    setLlmStatus(event.message);
                    setLlmLog((prev) => [...prev, event.message]);
                  } else if (event.type === 'progress') {
                    setLlmProgress(
                      `${event.total_chars.toLocaleString()} chars generated | ${event.elapsed}s | ${event.tokens_per_sec} tok/s`
                    );
                  } else if (event.type === 'complete') {
                    setLlmStatus('Parsing LLM response...');
                    const summary = `Done: ${event.total_chars.toLocaleString()} chars in ${event.elapsed}s (${event.tokens_per_sec} tok/s)`;
                    setLlmProgress(summary);
                    setLlmLog((prev) => [...prev, summary]);
                  } else if (event.type === 'done') {
                    resolve(event.document as Document);
                    return;
                  } else if (event.type === 'error') {
                    reject(new Error(event.message));
                    return;
                  }
                } catch {
                  // ignore parse errors for incomplete chunks
                }
              }
            }

            reject(new Error('Stream ended without result'));
          })
          .catch(reject);
      });

      setDocument(extractionResult);
      if (extractionResult.extracted_data) {
        setExtractedTrade(extractionResult.extracted_data);
      }
      setLlmStatus('');
      updateStepStatus('entity_extraction', 'complete');
    } catch (error) {
      updateStepStatus('entity_extraction', 'error');
      setStepErrors((prev) => ({ ...prev, entity_extraction: String(error) }));
      setLlmStatus('');
      setIsRunning(false);
      return;
    }

    // Step 4: Trade Comparison (expand but don't scroll — keep focus on entity extraction)
    updateStepStatus('comparison', 'processing');
    expandStep('comparison', false);
    try {
      const response = await fetch(`${API_BASE}/api/documents/${docId}/validate`, { method: 'POST' });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Validation failed');
      }
      const updatedDoc: Document = await response.json();
      setDocument(updatedDoc);
      if (updatedDoc.validation_result) {
        setValidationResult(updatedDoc.validation_result);
        setOverrideStatus(updatedDoc.validation_result.status === 'PENDING' ? 'MATCH' : updatedDoc.validation_result.status);
        setOverrideTradeId(
          updatedDoc.validation_result.system_trade_id === 'NOT_FOUND' ? '' : updatedDoc.validation_result.system_trade_id,
        );
      }
      updateStepStatus('comparison', 'complete');
    } catch (error) {
      updateStepStatus('comparison', 'error');
      setStepErrors((prev) => ({ ...prev, comparison: String(error) }));
      setIsRunning(false);
      return;
    }

    // Step 5: Human Review is now available
    expandStep('review', false);
    setIsRunning(false);
  };

  // -- Checker actions --

  const sendCheckerAction = async (decision: 'APPROVE' | 'REJECT' | 'OVERRIDE') => {
    if (!validationResult) return;

    const payload: Record<string, string> = {
      decision,
      comment: checkerComment,
    };

    if (decision === 'OVERRIDE') {
      payload.override_status = overrideStatus;
      if (overrideTradeId.trim()) {
        payload.override_system_trade_id = overrideTradeId.trim();
      }
    }

    try {
      const response = await fetch(`${API_BASE}/api/validations/${validationResult.id}/checker`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const updated: ValidationResult = await response.json();
        setValidationResult(updated);
        setCheckerSubmitted(true);
        updateStepStatus('review', 'complete');
      }
    } catch (error) {
      console.error('Checker action failed:', error);
    }
  };

  // -- Render helpers --

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf':
        return <FileText className="h-5 w-5 text-red-600" />;
      case 'image':
        return <Image className="h-5 w-5 text-blue-600" />;
      case 'docx':
        return <FileText className="h-5 w-5 text-blue-700" />;
      case 'msg':
        return <Mail className="h-5 w-5 text-amber-600" />;
      default:
        return <File className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStepStatusIcon = (status: PipelineStepStatus) => {
    switch (status) {
      case 'complete':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Circle className="h-5 w-5 text-muted-foreground/40" />;
    }
  };

  const getMatchStatusColor = (status: FieldComparison['match_status']) => {
    switch (status) {
      case 'MATCH':
        return 'bg-green-50 border-green-200';
      case 'WITHIN_TOLERANCE':
        return 'bg-yellow-50 border-yellow-200';
      case 'LOW_CONFIDENCE':
        return 'bg-orange-50 border-orange-200';
      case 'MISMATCH':
        return 'bg-red-50 border-red-200';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.5) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getStatusBadge = (status: ValidationResult['status']) => {
    switch (status) {
      case 'MATCH':
        return <Badge variant="success">Match</Badge>;
      case 'PARTIAL':
        return <Badge variant="warning">Partial</Badge>;
      case 'MISMATCH':
        return <Badge variant="destructive">Mismatch</Badge>;
      default:
        return <Badge variant="secondary">Pending</Badge>;
    }
  };

  const pipelineStarted = stepStatuses.upload === 'complete';
  const pipelineComplete = stepStatuses.comparison === 'complete';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Validation Pipeline</h1>
          <p className="text-muted-foreground">
            Upload trade evidence and process through extraction, comparison, and review.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {pipelineStarted && !isRunning && !pipelineComplete && (
            <Button onClick={runPipeline}>
              <Play className="mr-2 h-4 w-4" />
              Run Pipeline
            </Button>
          )}
          {(pipelineStarted || document) && (
            <Button variant="outline" onClick={resetPipeline}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Start Over
            </Button>
          )}
        </div>
      </div>

      <div className="flex gap-6">
        {/* Left sidebar stepper */}
        <div className="hidden md:block w-56 shrink-0">
          <div className="sticky top-8 space-y-1">
            {STEPS.map((step, index) => {
              const status = stepStatuses[step.key];
              const isActive = status === 'processing';
              const isComplete = status === 'complete';
              const isError = status === 'error';

              return (
                <div key={step.key}>
                  <button
                    className={cn(
                      'w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors text-left',
                      isActive && 'bg-blue-50 text-blue-800 font-medium',
                      isComplete && 'text-green-800',
                      isError && 'text-red-800',
                      !isActive && !isComplete && !isError && 'text-muted-foreground',
                    )}
                    onClick={() => toggleStep(step.key)}
                  >
                    {getStepStatusIcon(status)}
                    <span className="truncate">{step.label}</span>
                  </button>
                  {index < STEPS.length - 1 && (
                    <div className="ml-5 h-4 border-l-2 border-muted-foreground/20" />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Main content area */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Step 1: Upload */}
          <StepCard
            ref={(el) => { stepRefs.current['upload'] = el; }}
            title="Inbound Evidence"
            stepNumber={1}
            status={stepStatuses.upload}
            icon={<Upload className="h-4 w-4" />}
            expanded={expandedSteps.has('upload')}
            onToggle={() => toggleStep('upload')}
            error={stepErrors.upload}
          >
            {!document ? (
              <Tabs defaultValue="file" className="space-y-4">
                <TabsList>
                  <TabsTrigger value="file">File Upload</TabsTrigger>
                  <TabsTrigger value="text">Text Input</TabsTrigger>
                </TabsList>

                <TabsContent value="file">
                  <div
                    className={cn(
                      'border-2 border-dashed rounded-lg p-10 text-center transition-colors',
                      isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25',
                    )}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                  >
                    <Upload className="mx-auto h-10 w-10 text-muted-foreground" />
                    <p className="mt-3 text-base font-medium">Drop client email or evidence file here</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Supports .msg, .pdf, .docx, images (PNG, JPG, BMP)
                    </p>
                    <input
                      type="file"
                      className="hidden"
                      id="pipeline-file-upload"
                      accept=".msg,.pdf,.docx,.png,.jpg,.jpeg,.gif,.bmp"
                      onChange={handleFileSelect}
                    />
                    <Button className="mt-4" asChild disabled={isUploading}>
                      <label htmlFor="pipeline-file-upload" className="cursor-pointer">
                        {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                        Browse Files
                      </label>
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent value="text">
                  <div className="space-y-3">
                    <Textarea
                      placeholder="Paste trade confirmation email text here..."
                      className="min-h-[180px] font-mono text-sm"
                      value={textInput}
                      onChange={(e) => setTextInput(e.target.value)}
                    />
                    <Button onClick={handleTextSubmit} disabled={isUploading || !textInput.trim()}>
                      {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      Submit Text
                    </Button>
                  </div>
                </TabsContent>
              </Tabs>
            ) : (
              <div className="flex items-center gap-4 p-3 bg-muted/50 rounded-lg">
                {getFileIcon(document.file_type)}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{document.filename}</p>
                  <p className="text-sm text-muted-foreground">
                    Type: {document.file_type.toUpperCase()} &middot; Uploaded: {new Date(document.upload_date).toLocaleString()}
                  </p>
                </div>
                <Badge variant="success">Uploaded</Badge>
              </div>
            )}
          </StepCard>

          {/* Step 2: Content Extraction */}
          <StepCard
            ref={(el) => { stepRefs.current['content_extraction'] = el; }}
            title="Content Extraction"
            stepNumber={2}
            status={stepStatuses.content_extraction}
            icon={<FileText className="h-4 w-4" />}
            expanded={expandedSteps.has('content_extraction')}
            onToggle={() => toggleStep('content_extraction')}
            error={stepErrors.content_extraction}
          >
            {stepStatuses.content_extraction === 'processing' && (
              <div className="flex items-center gap-3 py-6 justify-center text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Extracting document content...</span>
              </div>
            )}
            {contentExtraction && (
              <div className="space-y-4">
                {/* Email metadata */}
                {(contentExtraction.email_subject || contentExtraction.email_sender) && (
                  <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Mail className="h-4 w-4" />
                      Email Metadata
                    </div>
                    {contentExtraction.email_subject && (
                      <div className="text-sm">
                        <span className="text-muted-foreground">Subject:</span>{' '}
                        <span className="font-medium">{contentExtraction.email_subject}</span>
                      </div>
                    )}
                    {contentExtraction.email_sender && (
                      <div className="text-sm">
                        <span className="text-muted-foreground">From:</span>{' '}
                        <span className="font-medium">{contentExtraction.email_sender}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Attachments */}
                {contentExtraction.attachments.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Paperclip className="h-4 w-4" />
                      Attachments ({contentExtraction.attachments.length})
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {contentExtraction.attachments.map((att, i) => (
                        <div key={i} className="flex items-center gap-3 border rounded-md p-3 text-sm">
                          {getFileIcon(att.source_type === 'image' ? 'image' : att.source_type)}
                          <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">{att.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {att.source_type} &middot; {att.text_length.toLocaleString()} chars extracted
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Images */}
                {contentExtraction.images.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Image className="h-4 w-4" />
                      Images ({contentExtraction.images.length})
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {contentExtraction.images.map((img, i) => (
                        <div key={i} className="flex items-center gap-3 border rounded-md p-3 text-sm">
                          <Image className="h-4 w-4 text-blue-600" />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">{img.name}</p>
                            <p className="text-xs text-muted-foreground">
                              OCR: {img.text_length.toLocaleString()} chars
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Warnings */}
                {contentExtraction.warnings.length > 0 && (
                  <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded p-3">
                    {contentExtraction.warnings.map((warning, i) => (
                      <div key={i}>- {warning}</div>
                    ))}
                  </div>
                )}

                {/* Raw text preview */}
                <div className="space-y-2">
                  <div className="text-sm font-medium">Extracted Text</div>
                  <div className="max-h-64 overflow-y-auto rounded-md border bg-muted/30 p-3">
                    <pre className="text-xs whitespace-pre-wrap font-mono text-muted-foreground">
                      {contentExtraction.raw_text.slice(0, 3000)}
                      {contentExtraction.raw_text.length > 3000 && '\n... (truncated)'}
                    </pre>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {contentExtraction.raw_text.length.toLocaleString()} total characters
                  </p>
                </div>
              </div>
            )}
          </StepCard>

          {/* Step 3: Entity Extraction */}
          <StepCard
            ref={(el) => { stepRefs.current['entity_extraction'] = el; }}
            title="Entity Extraction"
            stepNumber={3}
            status={stepStatuses.entity_extraction}
            icon={<Sparkles className="h-4 w-4" />}
            expanded={expandedSteps.has('entity_extraction')}
            onToggle={() => toggleStep('entity_extraction')}
            error={stepErrors.entity_extraction}
          >
            {stepStatuses.entity_extraction === 'processing' && (
              <div className="space-y-3 py-4">
                <div className="flex items-center gap-3">
                  <Loader2 className="h-5 w-5 animate-spin text-blue-600 shrink-0" />
                  <span className="text-sm font-medium text-blue-700">{llmStatus || 'Extracting structured trade fields via LLM...'}</span>
                </div>
                {llmProgress && (
                  <div className="text-xs text-muted-foreground font-mono pl-8">{llmProgress}</div>
                )}
                {llmLog.length > 0 && (
                  <div className="max-h-32 overflow-y-auto rounded-md border bg-muted/50 p-3 mx-2">
                    {llmLog.map((entry, i) => (
                      <div
                        key={i}
                        className="text-xs text-muted-foreground font-mono py-0.5"
                        ref={i === llmLog.length - 1 ? (el) => el?.scrollIntoView({ behavior: 'smooth', block: 'end' }) : undefined}
                      >
                        <span className="text-muted-foreground/50 mr-2">{i + 1}.</span>
                        {entry}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {extractedTrade && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Badge>{extractedTrade.trade_type}</Badge>
                  {extractedTrade.schema_version && (
                    <span className="text-xs text-muted-foreground">Schema: {extractedTrade.schema_version}</span>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {Object.entries(extractedTrade.fields)
                    .sort(([, a], [, b]) => a.confidence - b.confidence)
                    .map(([field, info]) => (
                      <div key={field} className="space-y-1.5 border rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium capitalize">{field.replace(/_/g, ' ')}</p>
                          <span
                            className={cn(
                              'text-xs font-medium px-1.5 py-0.5 rounded',
                              info.confidence >= 0.8 && 'bg-green-100 text-green-800',
                              info.confidence >= 0.5 && info.confidence < 0.8 && 'bg-yellow-100 text-yellow-800',
                              info.confidence < 0.5 && 'bg-red-100 text-red-800',
                            )}
                          >
                            {(info.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="font-mono text-sm">{String(info.value ?? '-')}</p>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className={cn('h-full rounded-full transition-all', getConfidenceColor(info.confidence))}
                            style={{ width: `${Math.max(0, info.confidence) * 100}%` }}
                          />
                        </div>
                        {info.provenance?.source_type && (
                          <p className="text-xs text-muted-foreground">
                            Source: {info.provenance.source_type}
                            {info.provenance.source_name ? ` (${info.provenance.source_name})` : ''}
                          </p>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            )}
          </StepCard>

          {/* Step 4: Trade Comparison */}
          <StepCard
            ref={(el) => { stepRefs.current['comparison'] = el; }}
            title="Trade Comparison"
            stepNumber={4}
            status={stepStatuses.comparison}
            icon={<Scale className="h-4 w-4" />}
            expanded={expandedSteps.has('comparison')}
            onToggle={() => toggleStep('comparison')}
            error={stepErrors.comparison}
          >
            {stepStatuses.comparison === 'processing' && (
              <div className="flex items-center gap-3 py-6 justify-center text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Comparing extracted fields with system trades...</span>
              </div>
            )}
            {validationResult && (
              <div className="space-y-4">
                {/* Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="border rounded-lg p-3">
                    <div className="text-xs text-muted-foreground">Overall Status</div>
                    <div className="mt-1">{getStatusBadge(validationResult.status)}</div>
                  </div>
                  <div className="border rounded-lg p-3">
                    <div className="text-xs text-muted-foreground">Matched Trade</div>
                    <div className="mt-1 font-mono text-sm font-medium">{validationResult.system_trade_id}</div>
                  </div>
                  <div className="border rounded-lg p-3">
                    <div className="text-xs text-muted-foreground">Machine Confidence</div>
                    <div className="mt-1 font-medium">
                      {((validationResult.machine_confidence || 0) * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="border rounded-lg p-3">
                    <div className="text-xs text-muted-foreground">Auto-passed</div>
                    <div className="mt-1">
                      {validationResult.auto_passed ? (
                        <Badge variant="success">Yes</Badge>
                      ) : (
                        <Badge variant="secondary">No</Badge>
                      )}
                    </div>
                  </div>
                </div>

                {/* Field comparisons */}
                <div className="space-y-2">
                  <div className="text-sm font-medium">Field-by-Field Comparison</div>
                  {validationResult.field_comparisons.length > 0 ? (
                    <div className="space-y-2">
                      {validationResult.field_comparisons.map((comparison, index) => (
                        <div
                          key={index}
                          className={cn('border rounded-lg p-3', getMatchStatusColor(comparison.match_status))}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-sm capitalize">
                              {comparison.field_name.replace(/_/g, ' ')}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {comparison.match_status.replace('_', ' ')}
                            </Badge>
                          </div>
                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                              <p className="text-xs text-muted-foreground">Extracted</p>
                              <p className="font-mono">{String(comparison.extracted_value ?? '-')}</p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">System</p>
                              <p className="font-mono">{String(comparison.system_value ?? '-')}</p>
                            </div>
                          </div>
                          <div className="mt-2 text-xs text-muted-foreground flex justify-between">
                            <span>{comparison.rule_applied || 'rule: n/a'}</span>
                            <span>Confidence: {(comparison.confidence * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground py-4 text-center">
                      No field comparisons available.
                    </div>
                  )}
                </div>
              </div>
            )}
          </StepCard>

          {/* Step 5: Human Review */}
          <StepCard
            ref={(el) => { stepRefs.current['review'] = el; }}
            title="Human Review"
            stepNumber={5}
            status={stepStatuses.review}
            icon={<UserCheck className="h-4 w-4" />}
            expanded={expandedSteps.has('review')}
            onToggle={() => toggleStep('review')}
            error={stepErrors.review}
          >
            {!validationResult && (
              <div className="text-sm text-muted-foreground py-6 text-center">
                Waiting for pipeline to reach comparison step...
              </div>
            )}
            {validationResult && !checkerSubmitted && (
              <div className="space-y-4">
                <div className="text-sm text-muted-foreground">
                  Review the extracted data and comparison results above, then approve, reject, or override.
                </div>

                <div className="space-y-3">
                  <div className="space-y-1">
                    <Label>Comment (optional)</Label>
                    <Input
                      value={checkerComment}
                      onChange={(e) => setCheckerComment(e.target.value)}
                      placeholder="Add a review comment..."
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label>Override Status</Label>
                      <Select
                        value={overrideStatus}
                        onValueChange={(v) => setOverrideStatus(v as 'MATCH' | 'PARTIAL' | 'MISMATCH')}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="MATCH">MATCH</SelectItem>
                          <SelectItem value="PARTIAL">PARTIAL</SelectItem>
                          <SelectItem value="MISMATCH">MISMATCH</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label>Override Trade ID (optional)</Label>
                      <Input
                        value={overrideTradeId}
                        onChange={(e) => setOverrideTradeId(e.target.value)}
                        placeholder="TRS-2026-001"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-2">
                    <Button onClick={() => sendCheckerAction('APPROVE')}>
                      <CheckCircle className="mr-2 h-4 w-4" />
                      Approve
                    </Button>
                    <Button variant="destructive" onClick={() => sendCheckerAction('REJECT')}>
                      <XCircle className="mr-2 h-4 w-4" />
                      Reject
                    </Button>
                    <Button variant="outline" onClick={() => sendCheckerAction('OVERRIDE')}>
                      Override
                    </Button>
                  </div>
                </div>
              </div>
            )}
            {validationResult && checkerSubmitted && (
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="font-medium text-green-800">Review Complete</p>
                    <p className="text-sm text-green-700">
                      Decision: {validationResult.checker_decision}
                      {validationResult.checker_comment && ` - "${validationResult.checker_comment}"`}
                    </p>
                    {validationResult.checked_at && (
                      <p className="text-xs text-green-600 mt-1">
                        {new Date(validationResult.checked_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </StepCard>
        </div>
      </div>
    </div>
  );
}

// -- Reusable Step Card component --

interface StepCardProps {
  title: string;
  stepNumber: number;
  status: PipelineStepStatus;
  icon: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  error?: string;
  children: React.ReactNode;
}

import { forwardRef } from 'react';

const StepCard = forwardRef<HTMLDivElement, StepCardProps>(
  ({ title, stepNumber, status, icon, expanded, onToggle, error, children }, ref) => {
    const getStatusIcon = (s: PipelineStepStatus) => {
      switch (s) {
        case 'complete':
          return <CheckCircle className="h-4 w-4 text-green-600" />;
        case 'processing':
          return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
        case 'error':
          return <XCircle className="h-4 w-4 text-red-600" />;
        default:
          return <Circle className="h-4 w-4 text-muted-foreground/40" />;
      }
    };

    return (
      <Card ref={ref} className={cn('overflow-hidden', status === 'processing' && 'ring-2 ring-blue-200')}>
        <button
          className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors text-left"
          onClick={onToggle}
        >
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center h-7 w-7 rounded-full bg-muted text-xs font-bold">
              {stepNumber}
            </div>
            {icon}
            <h3 className="font-semibold text-sm">{title}</h3>
            {getStatusIcon(status)}
          </div>
          <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', expanded && 'rotate-180')} />
        </button>
        {expanded && (
          <CardContent className="pt-0 border-t">
            {error && (
              <div className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3 mb-4">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {children}
          </CardContent>
        )}
      </Card>
    );
  },
);

StepCard.displayName = 'StepCard';
