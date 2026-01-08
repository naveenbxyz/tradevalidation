import { useState, useEffect, useRef } from 'react';
import { Loader2, ZoomIn, ZoomOut, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { DocumentViewerData, FieldCoordinate } from '@/types/trade';

const API_BASE = 'http://localhost:8000';

// Color palette for different field types
const FIELD_COLORS: Record<string, string> = {
  trade_id: '#3b82f6',      // blue
  counterparty: '#8b5cf6',   // purple
  trade_date: '#10b981',     // green
  effective_date: '#10b981', // green
  maturity_date: '#f59e0b',  // amber
  value_date: '#f59e0b',     // amber
  notional: '#ef4444',       // red
  rate: '#ec4899',           // pink
  fixed_rate: '#ec4899',     // pink
  floating_rate: '#f97316',  // orange
  floating_index: '#06b6d4', // cyan
  currency: '#6366f1',       // indigo
  currency_pair: '#6366f1',  // indigo
  direction: '#84cc16',      // lime
  spread: '#14b8a6',         // teal
  payment_frequency: '#a855f7', // purple
  trade_type: '#64748b',     // slate
};

function getFieldColor(fieldName: string): string {
  return FIELD_COLORS[fieldName] || '#6b7280'; // default gray
}

interface DocumentViewerProps {
  documentId: string;
  onClose?: () => void;
}

export function DocumentViewer({ documentId, onClose }: DocumentViewerProps) {
  const [viewerData, setViewerData] = useState<DocumentViewerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [showHighlights, setShowHighlights] = useState(true);
  const [hoveredField, setHoveredField] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function fetchViewerData() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_BASE}/api/documents/${documentId}/viewer`);
        if (!response.ok) {
          throw new Error('Failed to load document viewer');
        }
        const data = await response.json();
        setViewerData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    fetchViewerData();
  }, [documentId]);

  const handleZoomIn = () => setZoom(z => Math.min(z + 0.25, 3));
  const handleZoomOut = () => setZoom(z => Math.max(z - 0.25, 0.5));

  if (loading) {
    return (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">Loading document...</span>
        </CardContent>
      </Card>
    );
  }

  if (error || !viewerData) {
    return (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center py-12">
          <p className="text-destructive">{error || 'Failed to load document'}</p>
        </CardContent>
      </Card>
    );
  }

  const fieldEntries = Object.entries(viewerData.field_coordinates);

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{viewerData.filename}</CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleZoomOut}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground w-12 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <Button variant="outline" size="sm" onClick={handleZoomIn}>
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button
              variant={showHighlights ? "default" : "outline"}
              size="sm"
              onClick={() => setShowHighlights(!showHighlights)}
            >
              {showHighlights ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            </Button>
            {onClose && (
              <Button variant="ghost" size="sm" onClick={onClose}>
                Close
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex gap-4">
          {/* Document Image with Overlays */}
          <div
            ref={containerRef}
            className="flex-1 overflow-auto border rounded-lg bg-gray-100"
            style={{ maxHeight: '70vh' }}
          >
            <div
              className="relative inline-block"
              style={{
                transform: `scale(${zoom})`,
                transformOrigin: 'top left',
              }}
            >
              <img
                src={`data:image/png;base64,${viewerData.image_base64}`}
                alt={viewerData.filename}
                className="block"
                style={{ maxWidth: 'none' }}
              />

              {/* Field Highlight Overlays */}
              {showHighlights && fieldEntries.map(([fieldName, coords]) => (
                <FieldHighlight
                  key={fieldName}
                  fieldName={fieldName}
                  coords={coords}
                  imageWidth={viewerData.image_width}
                  imageHeight={viewerData.image_height}
                  isHovered={hoveredField === fieldName}
                  onMouseEnter={() => setHoveredField(fieldName)}
                  onMouseLeave={() => setHoveredField(null)}
                />
              ))}
            </div>
          </div>

          {/* Field Legend */}
          <div className="w-64 shrink-0">
            <h4 className="font-semibold mb-3">Extracted Fields</h4>
            <div className="space-y-2 max-h-[60vh] overflow-y-auto">
              {fieldEntries.map(([fieldName, coords]) => (
                <div
                  key={fieldName}
                  className={`p-2 rounded-lg border cursor-pointer transition-colors ${
                    hoveredField === fieldName ? 'bg-accent' : 'hover:bg-accent/50'
                  }`}
                  onMouseEnter={() => setHoveredField(fieldName)}
                  onMouseLeave={() => setHoveredField(null)}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div
                      className="w-3 h-3 rounded-full shrink-0"
                      style={{ backgroundColor: getFieldColor(fieldName) }}
                    />
                    <span className="text-sm font-medium capitalize">
                      {fieldName.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground truncate pl-5">
                    {coords.field_value}
                  </p>
                </div>
              ))}

              {fieldEntries.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No field coordinates found. Extract the document first.
                </p>
              )}
            </div>

            {/* Match Status Legend */}
            <div className="mt-4 pt-4 border-t">
              <h4 className="font-semibold mb-2 text-sm">Legend</h4>
              <div className="space-y-1 text-xs text-muted-foreground">
                <p>Hover over fields to highlight on document</p>
                <p>Colors indicate different field types</p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface FieldHighlightProps {
  fieldName: string;
  coords: FieldCoordinate;
  imageWidth: number;
  imageHeight: number;
  isHovered: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

function FieldHighlight({
  fieldName,
  coords,
  imageWidth,
  imageHeight,
  isHovered,
  onMouseEnter,
  onMouseLeave,
}: FieldHighlightProps) {
  const color = getFieldColor(fieldName);

  // Convert normalized coordinates to pixels
  const left = coords.x * imageWidth;
  const top = coords.y * imageHeight;
  const width = coords.width * imageWidth;
  const height = coords.height * imageHeight;

  // Add some padding
  const padding = 4;

  return (
    <div
      className="absolute pointer-events-auto cursor-pointer transition-all"
      style={{
        left: left - padding,
        top: top - padding,
        width: width + padding * 2,
        height: height + padding * 2,
        backgroundColor: isHovered ? `${color}33` : `${color}22`,
        border: `2px solid ${color}`,
        borderRadius: 4,
        boxShadow: isHovered ? `0 0 8px ${color}66` : 'none',
      }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {isHovered && (
        <div
          className="absolute left-0 -top-8 px-2 py-1 rounded text-xs text-white whitespace-nowrap z-10"
          style={{ backgroundColor: color }}
        >
          {fieldName.replace(/_/g, ' ')}: {coords.field_value}
        </div>
      )}
    </div>
  );
}
