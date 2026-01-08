import { useState, useCallback } from 'react';
import { Upload, FileText, Image, File, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { Document, ExtractedTrade } from '@/types/trade';

const API_BASE = 'http://localhost:8000';

export function DocumentUpload() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [textInput, setTextInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

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

        if (response.ok) {
          const doc = await response.json();
          setDocuments(prev => [...prev, doc]);
        }
      } catch (error) {
        console.error('Upload failed:', error);
      }
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

      if (response.ok) {
        const doc = await response.json();
        setDocuments(prev => [...prev, doc]);
        setTextInput('');
      }
    } catch (error) {
      console.error('Text submission failed:', error);
    }
    setIsUploading(false);
  };

  const processDocument = async (docId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${docId}/extract`, {
        method: 'POST',
      });

      if (response.ok) {
        const updatedDoc = await response.json();
        setDocuments(prev => prev.map(d => d.id === docId ? updatedDoc : d));
      }
    } catch (error) {
      console.error('Extraction failed:', error);
    }
  };

  const validateDocument = async (docId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${docId}/validate`, {
        method: 'POST',
      });

      if (response.ok) {
        const updatedDoc = await response.json();
        setDocuments(prev => prev.map(d => d.id === docId ? updatedDoc : d));
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf': return <FileText className="h-5 w-5" />;
      case 'image': return <Image className="h-5 w-5" />;
      default: return <File className="h-5 w-5" />;
    }
  };

  const getStatusBadge = (status: Document['status']) => {
    switch (status) {
      case 'PENDING': return <Badge variant="secondary">Pending</Badge>;
      case 'PROCESSING': return <Badge variant="outline">Processing</Badge>;
      case 'EXTRACTED': return <Badge variant="default">Extracted</Badge>;
      case 'VALIDATED': return <Badge variant="success">Validated</Badge>;
      case 'ERROR': return <Badge variant="destructive">Error</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Document Upload</h1>
        <p className="text-muted-foreground">
          Upload trade confirmation documents for validation
        </p>
      </div>

      <Tabs defaultValue="file" className="space-y-4">
        <TabsList>
          <TabsTrigger value="file">File Upload</TabsTrigger>
          <TabsTrigger value="text">Text Input</TabsTrigger>
        </TabsList>

        <TabsContent value="file">
          <Card>
            <CardHeader>
              <CardTitle>Upload Documents</CardTitle>
              <CardDescription>
                Drag and drop PDF files, images, or click to browse
              </CardDescription>
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
                <p className="mt-4 text-lg font-medium">
                  Drop files here or click to upload
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Supports PDF, PNG, JPG, and other image formats
                </p>
                <input
                  type="file"
                  className="hidden"
                  id="file-upload"
                  multiple
                  accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp"
                  onChange={handleFileSelect}
                />
                <Button className="mt-4" asChild>
                  <label htmlFor="file-upload" className="cursor-pointer">
                    Browse Files
                  </label>
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="text">
          <Card>
            <CardHeader>
              <CardTitle>Paste Trade Confirmation</CardTitle>
              <CardDescription>
                Paste email content or trade details as text
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="Paste trade confirmation text here...

Example:
Trade Confirmation
Counterparty: Goldman Sachs
Trade Type: FX Spot
Currency Pair: EUR/USD
Direction: BUY
Notional: 1,000,000 EUR
Rate: 1.0850
Trade Date: 2024-01-15
Value Date: 2024-01-17"
                className="min-h-[200px] font-mono"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
              />
              <Button onClick={handleTextSubmit} disabled={isUploading || !textInput.trim()}>
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  'Submit Text'
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {documents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Uploaded Documents</CardTitle>
            <CardDescription>
              {documents.length} document(s) uploaded
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center space-x-4">
                    {getFileIcon(doc.file_type)}
                    <div>
                      <p className="font-medium">{doc.filename}</p>
                      <p className="text-sm text-muted-foreground">
                        Uploaded: {new Date(doc.upload_date).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    {getStatusBadge(doc.status)}
                    {doc.status === 'PENDING' && (
                      <Button size="sm" onClick={() => processDocument(doc.id)}>
                        Extract
                      </Button>
                    )}
                    {doc.status === 'EXTRACTED' && (
                      <Button size="sm" onClick={() => validateDocument(doc.id)}>
                        Validate
                      </Button>
                    )}
                    {doc.status === 'VALIDATED' && doc.validation_result && (
                      <div className="flex items-center space-x-2">
                        {doc.validation_result.status === 'MATCH' ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-500" />
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {documents.some(d => d.extracted_data) && (
        <Card>
          <CardHeader>
            <CardTitle>Extracted Data</CardTitle>
            <CardDescription>
              Trade data extracted from documents using LLM
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {documents.filter(d => d.extracted_data).map((doc) => (
                <ExtractedDataDisplay key={doc.id} document={doc} />
              ))}
            </div>
          </CardContent>
        </Card>
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
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {Object.entries(data.fields).map(([field, info]) => (
          <div key={field} className="space-y-1">
            <p className="text-sm text-muted-foreground capitalize">
              {field.replace(/_/g, ' ')}
            </p>
            <p className="font-medium">{String(info.value)}</p>
            <div className="h-1 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary"
                style={{ width: `${info.confidence * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
