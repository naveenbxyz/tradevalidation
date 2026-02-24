import { useCallback, useEffect, useState } from 'react';
import { Eye, File, FileText, FolderSearch, Image, Loader2, Mail, Upload } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { DocumentViewer } from '@/components/DocumentViewer';
import type { Document, ExtractedTrade } from '@/types/trade';

const API_BASE = 'http://localhost:8000';

export function DocumentUpload() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [textInput, setTextInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [viewingDocumentId, setViewingDocumentId] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/documents`);
      if (response.ok) {
        setDocuments(await response.json());
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };

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
    await uploadFiles(files);
  }, []);

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      await uploadFiles(files);
    }
  }, []);

  const uploadFiles = async (files: File[]) => {
    setIsUploading(true);
    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch(`${API_BASE}/api/documents/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const err = await response.json();
          console.error('Upload failed:', err.detail);
        }
      } catch (error) {
        console.error('Upload failed:', error);
      }
    }
    setIsUploading(false);
    await fetchDocuments();
  };

  const handleScanFolder = async () => {
    setIsScanning(true);
    try {
      await fetch(`${API_BASE}/api/documents/scan-folder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      await fetchDocuments();
    } catch (error) {
      console.error('Folder scan failed:', error);
    }
    setIsScanning(false);
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

      if (response.ok) {
        setTextInput('');
        await fetchDocuments();
      }
    } catch (error) {
      console.error('Text submission failed:', error);
    }
    setIsUploading(false);
  };

  const processDocument = async (docId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${docId}/extract`, { method: 'POST' });
      if (response.ok) {
        await fetchDocuments();
      }
    } catch (error) {
      console.error('Extraction failed:', error);
    }
  };

  const validateDocument = async (docId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${docId}/validate`, { method: 'POST' });
      if (response.ok) {
        await fetchDocuments();
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf':
        return <FileText className="h-5 w-5" />;
      case 'image':
        return <Image className="h-5 w-5" />;
      case 'docx':
        return <FileText className="h-5 w-5" />;
      case 'msg':
        return <Mail className="h-5 w-5" />;
      default:
        return <File className="h-5 w-5" />;
    }
  };

  const getStatusBadge = (status: Document['status']) => {
    switch (status) {
      case 'PENDING':
        return <Badge variant="secondary">Pending</Badge>;
      case 'PROCESSING':
        return <Badge variant="outline">Processing</Badge>;
      case 'EXTRACTED':
        return <Badge variant="default">Extracted</Badge>;
      case 'VALIDATED':
        return <Badge variant="success">Validated</Badge>;
      case 'ERROR':
        return <Badge variant="destructive">Error</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Evidence Ingestion</h1>
          <p className="text-muted-foreground">Upload `.msg`, PDF, DOCX, image evidence or submit plain text.</p>
        </div>
        <Button variant="outline" onClick={handleScanFolder} disabled={isScanning}>
          {isScanning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FolderSearch className="mr-2 h-4 w-4" />}
          Scan Predefined Folder
        </Button>
      </div>

      <Tabs defaultValue="file" className="space-y-4">
        <TabsList>
          <TabsTrigger value="file">File Upload</TabsTrigger>
          <TabsTrigger value="text">Text Input</TabsTrigger>
        </TabsList>

        <TabsContent value="file">
          <Card>
            <CardHeader>
              <CardTitle>Upload Evidence</CardTitle>
              <CardDescription>Drop files or browse. Supported: `.msg`, `.pdf`, `.docx`, images.</CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                  isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
                <p className="mt-4 text-lg font-medium">Drop files here or click to upload</p>
                <p className="mt-2 text-sm text-muted-foreground">TRS confirmation evidence in email or attachments</p>
                <input
                  type="file"
                  className="hidden"
                  id="file-upload"
                  multiple
                  accept=".msg,.pdf,.docx,.png,.jpg,.jpeg,.gif,.bmp"
                  onChange={handleFileSelect}
                />
                <Button className="mt-4" asChild>
                  <label htmlFor="file-upload" className="cursor-pointer">Browse Files</label>
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="text">
          <Card>
            <CardHeader>
              <CardTitle>Paste Email Text</CardTitle>
              <CardDescription>Use for quick experiments before integrating full mailbox ingestion.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="Paste TRS trade evidence text here..."
                className="min-h-[220px] font-mono"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
              />
              <Button onClick={handleTextSubmit} disabled={isUploading || !textInput.trim()}>
                {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Submit Text
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
          <CardDescription>{documents.length} item(s) in evidence queue</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {documents.map((doc) => (
              <div key={doc.id} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    {getFileIcon(doc.file_type)}
                    <div>
                      <p className="font-medium">{doc.filename}</p>
                      <p className="text-sm text-muted-foreground">Uploaded: {new Date(doc.upload_date).toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {getStatusBadge(doc.status)}
                    {(doc.file_type === 'pdf' || doc.file_type === 'image') && (
                      <Button size="sm" variant="outline" onClick={() => setViewingDocumentId(doc.id)}>
                        <Eye className="h-4 w-4 mr-1" />
                        View
                      </Button>
                    )}
                    {doc.status === 'PENDING' && <Button size="sm" onClick={() => processDocument(doc.id)}>Extract</Button>}
                    {doc.status === 'EXTRACTED' && <Button size="sm" onClick={() => validateDocument(doc.id)}>Validate</Button>}
                  </div>
                </div>

                {doc.processing_warnings && doc.processing_warnings.length > 0 && (
                  <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                    {doc.processing_warnings.map((warning, index) => (
                      <div key={index}>- {warning}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {documents.length === 0 && (
              <div className="text-center text-muted-foreground py-8">No evidence uploaded yet.</div>
            )}
          </div>
        </CardContent>
      </Card>

      {documents.some((d) => d.extracted_data) && (
        <Card>
          <CardHeader>
            <CardTitle>Structured Extraction</CardTitle>
            <CardDescription>LLM output with field-level confidence from TRS schema.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {documents.filter((d) => d.extracted_data).map((doc) => (
                <ExtractedDataDisplay key={doc.id} document={doc} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {viewingDocumentId && (
        <DocumentViewer documentId={viewingDocumentId} onClose={() => setViewingDocumentId(null)} />
      )}
    </div>
  );
}

function ExtractedDataDisplay({ document }: { document: Document }) {
  const data = document.extracted_data as ExtractedTrade;
  if (!data) return null;

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold">{document.filename}</h4>
        <Badge>{data.trade_type}</Badge>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(data.fields).map(([field, info]) => (
          <div key={field} className="space-y-1 border rounded p-3">
            <p className="text-sm text-muted-foreground capitalize">{field.replace(/_/g, ' ')}</p>
            <p className="font-medium">{String(info.value ?? '-')}</p>
            <div className="h-1 bg-muted rounded-full overflow-hidden">
              <div className="h-full bg-primary" style={{ width: `${Math.max(0, info.confidence) * 100}%` }} />
            </div>
            <p className="text-xs text-muted-foreground">Confidence: {(info.confidence * 100).toFixed(0)}%</p>
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
  );
}
