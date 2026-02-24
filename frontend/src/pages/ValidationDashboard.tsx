import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, CheckCircle, Download, Eye, RefreshCw, XCircle } from 'lucide-react';
import { ChatBubble } from '@/components/ChatBubble';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { FieldComparison, ValidationResult } from '@/types/trade';

const API_BASE = 'http://localhost:8000';

export function ValidationDashboard() {
  const [results, setResults] = useState<ValidationResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<ValidationResult | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [checkerComment, setCheckerComment] = useState('');
  const [overrideStatus, setOverrideStatus] = useState<'MATCH' | 'PARTIAL' | 'MISMATCH'>('MATCH');
  const [overrideTradeId, setOverrideTradeId] = useState('');

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

  const downloadReport = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/validations/report`);
      if (!response.ok) return;
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'trs_validation_report.csv';
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download report:', error);
    }
  };

  const handleViewDetails = (result: ValidationResult) => {
    setSelectedResult(result);
    setCheckerComment(result.checker_comment || '');
    setOverrideStatus(result.status === 'PENDING' ? 'MATCH' : result.status);
    setOverrideTradeId(result.system_trade_id === 'NOT_FOUND' ? '' : result.system_trade_id);
    setIsModalOpen(true);
  };

  const sendCheckerAction = async (decision: 'APPROVE' | 'REJECT' | 'OVERRIDE') => {
    if (!selectedResult) return;

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
      const response = await fetch(`${API_BASE}/api/validations/${selectedResult.id}/checker`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const updated = await response.json();
        setResults((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
        setSelectedResult(updated);
      }
    } catch (error) {
      console.error('Failed to submit checker action:', error);
    }
  };

  const stats = useMemo(() => {
    return {
      total: results.length,
      matched: results.filter((r) => r.status === 'MATCH').length,
      partial: results.filter((r) => r.status === 'PARTIAL').length,
      mismatched: results.filter((r) => r.status === 'MISMATCH').length,
      approved: results.filter((r) => r.checker_decision === 'APPROVED').length,
      rejected: results.filter((r) => r.checker_decision === 'REJECTED').length,
      overridden: results.filter((r) => r.checker_decision === 'OVERRIDDEN').length,
    };
  }, [results]);

  const getStatusIcon = (status: ValidationResult['status']) => {
    switch (status) {
      case 'MATCH':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'PARTIAL':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />;
      case 'MISMATCH':
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <RefreshCw className="h-4 w-4 text-muted-foreground animate-spin" />;
    }
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

  const getCheckerBadge = (decision: ValidationResult['checker_decision']) => {
    switch (decision) {
      case 'APPROVED':
        return <Badge variant="success">Approved</Badge>;
      case 'REJECTED':
        return <Badge variant="destructive">Rejected</Badge>;
      case 'OVERRIDDEN':
        return <Badge variant="warning">Overridden</Badge>;
      default:
        return <Badge variant="secondary">Pending</Badge>;
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">TRS Validation Dashboard</h1>
          <p className="text-muted-foreground">Machine validation outcomes with checker decisions and overrides.</p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={downloadReport}>
            <Download className="mr-2 h-4 w-4" />
            Download Report
          </Button>
          <Button variant="outline" onClick={fetchResults} disabled={isLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4 lg:grid-cols-7">
        <StatCard label="Total" value={stats.total} />
        <StatCard label="Match" value={stats.matched} tone="green" />
        <StatCard label="Partial" value={stats.partial} tone="yellow" />
        <StatCard label="Mismatch" value={stats.mismatched} tone="red" />
        <StatCard label="Approved" value={stats.approved} tone="green" />
        <StatCard label="Rejected" value={stats.rejected} tone="red" />
        <StatCard label="Overridden" value={stats.overridden} tone="yellow" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Validation Results</CardTitle>
          <CardDescription>Use View to inspect field-level evidence and apply checker action.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Checker</TableHead>
                <TableHead>Party B</TableHead>
                <TableHead>Trade Date</TableHead>
                <TableHead className="text-right">Notional</TableHead>
                <TableHead>Trade Match</TableHead>
                <TableHead className="text-right">Confidence</TableHead>
                <TableHead>Auto-pass</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((result) => (
                <TableRow key={result.id}>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(result.status)}
                      {getStatusBadge(result.status)}
                    </div>
                  </TableCell>
                  <TableCell>{getCheckerBadge(result.checker_decision)}</TableCell>
                  <TableCell className="font-medium">{result.party_b || '-'}</TableCell>
                  <TableCell>{result.trade_date || '-'}</TableCell>
                  <TableCell className="text-right font-mono">
                    {result.local_currency || '-'} {result.notional_amount?.toLocaleString() || '-'}
                  </TableCell>
                  <TableCell className="font-mono text-sm">{result.system_trade_id}</TableCell>
                  <TableCell className="text-right">{((result.machine_confidence || 0) * 100).toFixed(0)}%</TableCell>
                  <TableCell>{result.auto_passed ? <Badge variant="success">Yes</Badge> : <Badge variant="secondary">No</Badge>}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => handleViewDetails(result)}>
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-muted-foreground py-10">
                    No results yet. Process and validate documents first.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Field Comparison & Checker Action</DialogTitle>
            <DialogDescription>
              Review machine comparisons before approving, rejecting, or overriding.
            </DialogDescription>
          </DialogHeader>

          {selectedResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <SummaryItem label="Party A" value={selectedResult.party_a || '-'} />
                <SummaryItem label="Party B" value={selectedResult.party_b || '-'} />
                <SummaryItem label="Machine Status" value={selectedResult.status} />
                <SummaryItem label="Checker" value={selectedResult.checker_decision} />
                <SummaryItem label="System Trade ID" value={selectedResult.system_trade_id} />
                <SummaryItem label="Machine Confidence" value={`${((selectedResult.machine_confidence || 0) * 100).toFixed(0)}%`} />
              </div>

              <div className="space-y-3">
                {selectedResult.field_comparisons.length > 0 ? (
                  selectedResult.field_comparisons.map((comparison, index) => (
                    <div key={index} className={`border rounded-lg p-4 ${getMatchStatusColor(comparison.match_status)}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold capitalize">{comparison.field_name.replace(/_/g, ' ')}</span>
                        <Badge variant="outline">{comparison.match_status.replace('_', ' ')}</Badge>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
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
                        <span>Confidence {(comparison.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground">No field comparison details available.</div>
                )}
              </div>

              <div className="space-y-3 border rounded-lg p-4">
                <h4 className="font-semibold">Checker Actions</h4>
                <div className="space-y-1">
                  <Label>Comment</Label>
                  <Input value={checkerComment} onChange={(e) => setCheckerComment(e.target.value)} placeholder="Optional comment" />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label>Override Status</Label>
                    <Select value={overrideStatus} onValueChange={(value) => setOverrideStatus(value as 'MATCH' | 'PARTIAL' | 'MISMATCH')}>
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
                    <Input value={overrideTradeId} onChange={(e) => setOverrideTradeId(e.target.value)} placeholder="TRS-2026-001" />
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <Button onClick={() => sendCheckerAction('APPROVE')}>Approve</Button>
                  <Button variant="destructive" onClick={() => sendCheckerAction('REJECT')}>Reject</Button>
                  <Button variant="outline" onClick={() => sendCheckerAction('OVERRIDE')}>Override Match</Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <ChatBubble validationResults={results} />
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="border rounded p-2">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  );
}

function StatCard({ label, value, tone = 'default' }: { label: string; value: number; tone?: 'default' | 'green' | 'red' | 'yellow' }) {
  const toneClass =
    tone === 'green' ? 'text-green-700' : tone === 'red' ? 'text-red-700' : tone === 'yellow' ? 'text-yellow-700' : '';

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${toneClass}`}>{value}</div>
      </CardContent>
    </Card>
  );
}
