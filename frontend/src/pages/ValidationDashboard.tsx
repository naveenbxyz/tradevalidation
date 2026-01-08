import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, RefreshCw, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ChatBubble } from '@/components/ChatBubble';
import type { ValidationResult, FieldComparison } from '@/types/trade';

const API_BASE = 'http://localhost:8000';

export function ValidationDashboard() {
  const [results, setResults] = useState<ValidationResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<ValidationResult | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/validations`);
      if (response.ok) {
        setResults(await response.json());
      }
    } catch (error) {
      console.error('Failed to fetch validation results:', error);
    }
    setIsLoading(false);
  };

  const handleViewDetails = (result: ValidationResult) => {
    setSelectedResult(result);
    setIsModalOpen(true);
  };

  const getStatusIcon = (status: ValidationResult['status']) => {
    switch (status) {
      case 'MATCH': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'MISMATCH': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'PARTIAL': return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default: return <RefreshCw className="h-4 w-4 text-muted-foreground animate-spin" />;
    }
  };

  const getStatusBadge = (status: ValidationResult['status']) => {
    switch (status) {
      case 'MATCH': return <Badge variant="success">Matched</Badge>;
      case 'MISMATCH': return <Badge variant="destructive">Not Matched</Badge>;
      case 'PARTIAL': return <Badge variant="warning">Partial Match</Badge>;
      default: return <Badge variant="secondary">Pending</Badge>;
    }
  };

  const getMatchStatusColor = (status: FieldComparison['match_status']) => {
    switch (status) {
      case 'MATCH': return 'bg-green-50 border-green-200';
      case 'WITHIN_TOLERANCE': return 'bg-yellow-50 border-yellow-200';
      case 'MISMATCH': return 'bg-red-50 border-red-200';
    }
  };

  const getProductBadgeColor = (product?: string) => {
    if (!product) return 'bg-gray-100 text-gray-800';
    if (product.startsWith('FX')) return 'bg-blue-100 text-blue-800';
    if (product === 'IRS') return 'bg-purple-100 text-purple-800';
    if (product === 'CCS') return 'bg-indigo-100 text-indigo-800';
    if (product === 'Commodity') return 'bg-amber-100 text-amber-800';
    return 'bg-gray-100 text-gray-800';
  };

  const formatNotional = (notional?: number, currency?: string) => {
    if (!notional) return '-';
    const formatted = new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(notional);
    return currency ? `${currency} ${formatted}` : formatted;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'text-muted-foreground';
    if (confidence >= 0.9) return 'text-green-600';
    if (confidence >= 0.7) return 'text-yellow-600';
    return 'text-red-600';
  };

  const calculateOverallConfidence = (comparisons: FieldComparison[]) => {
    if (!comparisons || comparisons.length === 0) return 0;
    const totalConfidence = comparisons.reduce((sum, c) => sum + c.confidence, 0);
    return totalConfidence / comparisons.length;
  };

  const stats = {
    total: results.length,
    matched: results.filter(r => r.status === 'MATCH').length,
    notMatched: results.filter(r => r.status === 'MISMATCH').length,
    partial: results.filter(r => r.status === 'PARTIAL').length,
    pending: results.filter(r => r.status === 'PENDING').length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Validation Dashboard</h1>
          <p className="text-muted-foreground">
            View and manage trade validation results
          </p>
        </div>
        <Button variant="outline" onClick={fetchResults} disabled={isLoading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Validations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Matched</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.matched}</div>
            <p className="text-xs text-muted-foreground">
              {stats.total > 0 ? ((stats.matched / stats.total) * 100).toFixed(1) : 0}% success rate
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Not Matched</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.notMatched}</div>
            <p className="text-xs text-muted-foreground">
              Requires review
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Partial Match</CardTitle>
            <AlertCircle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats.partial}</div>
            <p className="text-xs text-muted-foreground">
              Needs attention
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Results Table */}
      <Card>
        <CardHeader>
          <CardTitle>Validation Results</CardTitle>
          <CardDescription>
            Click "View" to see detailed field comparison
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[130px]">Status</TableHead>
                <TableHead>Counterparty</TableHead>
                <TableHead>Product</TableHead>
                <TableHead>Trade Date</TableHead>
                <TableHead className="text-right">Notional</TableHead>
                <TableHead>Eff/Mat Date</TableHead>
                <TableHead>Trade ID</TableHead>
                <TableHead className="text-right">Confidence</TableHead>
                <TableHead className="w-[80px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((result) => {
                const confidence = result.confidence ?? calculateOverallConfidence(result.field_comparisons);
                const isNotMatched = result.status === 'MISMATCH' || result.system_trade_id === 'NOT_FOUND';

                return (
                  <TableRow key={result.id}>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(result.status)}
                        {getStatusBadge(result.status)}
                      </div>
                    </TableCell>
                    <TableCell className="font-medium">
                      {result.counterparty || '-'}
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getProductBadgeColor(result.product)}`}>
                        {result.product || '-'}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(result.trade_date)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatNotional(result.notional, result.currency)}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {result.effective_date ? formatDate(result.effective_date) : formatDate(result.maturity_date)}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {isNotMatched ? (
                        <span className="text-muted-foreground italic">-</span>
                      ) : (
                        result.system_trade_id
                      )}
                    </TableCell>
                    <TableCell className={`text-right font-medium ${getConfidenceColor(confidence)}`}>
                      {(confidence * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewDetails(result)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
              {results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-muted-foreground py-12">
                    No validation results yet. Upload and validate documents to see results.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Field Comparison Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              {selectedResult && getStatusIcon(selectedResult.status)}
              <span>Field Comparison</span>
            </DialogTitle>
            <DialogDescription>
              {selectedResult && (
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between">
                    <span>Counterparty:</span>
                    <span className="font-medium">{selectedResult.counterparty || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Product:</span>
                    <span className="font-medium">{selectedResult.product || '-'}</span>
                  </div>
                  {selectedResult.status !== 'MISMATCH' && selectedResult.system_trade_id !== 'NOT_FOUND' && (
                    <div className="flex justify-between">
                      <span>Matched Trade:</span>
                      <span className="font-mono font-medium">{selectedResult.system_trade_id}</span>
                    </div>
                  )}
                </div>
              )}
            </DialogDescription>
          </DialogHeader>

          {selectedResult && (
            <div className="space-y-3 mt-4">
              {selectedResult.field_comparisons.length > 0 ? (
                selectedResult.field_comparisons.map((comparison, index) => (
                  <div
                    key={index}
                    className={`border rounded-lg p-4 ${getMatchStatusColor(comparison.match_status)}`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-semibold capitalize">
                        {comparison.field_name.replace(/_/g, ' ')}
                      </span>
                      <div className="flex items-center space-x-2">
                        {comparison.match_status === 'MATCH' && (
                          <Badge variant="success">Match</Badge>
                        )}
                        {comparison.match_status === 'WITHIN_TOLERANCE' && (
                          <Badge variant="warning">Within Tolerance</Badge>
                        )}
                        {comparison.match_status === 'MISMATCH' && (
                          <Badge variant="destructive">Mismatch</Badge>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="bg-white/50 rounded p-2">
                        <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Extracted (Document)</p>
                        <p className="font-mono font-medium">{String(comparison.extracted_value)}</p>
                      </div>
                      <div className="bg-white/50 rounded p-2">
                        <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">System Record</p>
                        <p className="font-mono font-medium">{String(comparison.system_value)}</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
                      {comparison.rule_applied && (
                        <span>Rule: {comparison.rule_applied}</span>
                      )}
                      <span className={getConfidenceColor(comparison.confidence)}>
                        Confidence: {(comparison.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  No field comparisons available. This document may not have been matched to any system trade.
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Chat Bubble */}
      <ChatBubble validationResults={results} />
    </div>
  );
}
