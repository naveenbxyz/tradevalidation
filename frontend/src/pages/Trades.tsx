import { useEffect, useState } from 'react';
import { Download, Pencil, Plus, Trash2, Upload } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import type { TRSTrade } from '@/types/trade';

const API_BASE = 'http://localhost:8000';

export function Trades() {
  const [trsTrades, setTrsTrades] = useState<TRSTrade[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [editingTrade, setEditingTrade] = useState<TRSTrade | null>(null);

  useEffect(() => {
    fetchTrades();
  }, []);

  const fetchTrades = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/trades/trs`);
      if (response.ok) {
        setTrsTrades(await response.json());
      }
    } catch (error) {
      console.error('Failed to fetch TRS trades:', error);
    }
  };

  const saveTrade = async (trade: Partial<TRSTrade>) => {
    const url = trade.id ? `${API_BASE}/api/trades/trs/${trade.id}` : `${API_BASE}/api/trades/trs`;
    const method = trade.id ? 'PUT' : 'POST';

    try {
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trade),
      });

      if (response.ok) {
        await fetchTrades();
        setIsAdding(false);
        setEditingTrade(null);
      }
    } catch (error) {
      console.error('Failed to save TRS trade:', error);
    }
  };

  const deleteTrade = async (id: string) => {
    try {
      await fetch(`${API_BASE}/api/trades/trs/${id}`, { method: 'DELETE' });
      await fetchTrades();
    } catch (error) {
      console.error('Failed to delete TRS trade:', error);
    }
  };

  const exportTrades = () => {
    const data = { trs_trades: trsTrades };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'trs_trades.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  const importTrades = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const payload = JSON.parse(await file.text());
      await fetch(`${API_BASE}/api/trades/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      await fetchTrades();
    } catch (error) {
      console.error('Failed to import TRS trades:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">TRS Source-of-Truth Trades</h1>
          <p className="text-muted-foreground">Manage simulated trade records used for automated validation.</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={exportTrades}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button variant="outline" asChild>
            <label className="cursor-pointer">
              <Upload className="mr-2 h-4 w-4" />
              Import
              <input className="hidden" type="file" accept=".json" onChange={importTrades} />
            </label>
          </Button>
          <Dialog open={isAdding} onOpenChange={setIsAdding}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Trade
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl">
              <TRSTradeForm onSave={saveTrade} onCancel={() => setIsAdding(false)} />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>TRS Trades ({trsTrades.length})</CardTitle>
          <CardDescription>These records represent the internal system-of-record for matching.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Trade ID</TableHead>
                <TableHead>Party B</TableHead>
                <TableHead>Trade Date</TableHead>
                <TableHead>Termination</TableHead>
                <TableHead>Local Notional</TableHead>
                <TableHead>USD Notional</TableHead>
                <TableHead>Payer / Receiver</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trsTrades.map((trade) => (
                <TableRow key={trade.id}>
                  <TableCell className="font-mono">{trade.trade_id}</TableCell>
                  <TableCell>{trade.party_b}</TableCell>
                  <TableCell>{trade.trade_date}</TableCell>
                  <TableCell>{trade.scheduled_termination_date}</TableCell>
                  <TableCell className="font-mono">{trade.local_currency} {trade.notional_amount.toLocaleString()}</TableCell>
                  <TableCell className="font-mono">USD {trade.usd_notional_amount.toLocaleString()}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{trade.bond_return_payer} / {trade.bond_return_receiver}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end space-x-2">
                      <Dialog open={editingTrade?.id === trade.id} onOpenChange={(open) => !open && setEditingTrade(null)}>
                        <DialogTrigger asChild>
                          <Button variant="ghost" size="icon" onClick={() => setEditingTrade(trade)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-4xl">
                          <TRSTradeForm trade={trade} onSave={saveTrade} onCancel={() => setEditingTrade(null)} />
                        </DialogContent>
                      </Dialog>
                      <Button variant="ghost" size="icon" onClick={() => deleteTrade(trade.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {trsTrades.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    No TRS trades found. Add or import records to start validation.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

interface TRSTradeFormProps {
  trade?: TRSTrade;
  onSave: (trade: Partial<TRSTrade>) => void;
  onCancel: () => void;
}

function TRSTradeForm({ trade, onSave, onCancel }: TRSTradeFormProps) {
  const [formData, setFormData] = useState<Partial<TRSTrade>>(
    trade || {
      trade_id: '',
      party_a: 'Acme Bank N.A.',
      party_b: '',
      trade_date: '',
      effective_date: '',
      scheduled_termination_date: '',
      bond_return_payer: 'PartyA',
      bond_return_receiver: 'PartyB',
      local_currency: 'USD',
      notional_amount: 0,
      usd_notional_amount: 0,
      initial_spot_rate: 1,
      current_market_price: 100,
      underlier: '',
      isin: '',
    }
  );

  const update = (field: keyof TRSTrade, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle>{trade ? 'Edit TRS Trade' : 'Add TRS Trade'}</DialogTitle>
      </DialogHeader>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Trade ID">
            <Input value={formData.trade_id || ''} onChange={(e) => update('trade_id', e.target.value)} required />
          </Field>
          <Field label="Party A">
            <Input value={formData.party_a || ''} onChange={(e) => update('party_a', e.target.value)} required />
          </Field>
          <Field label="Party B (Counterparty)">
            <Input value={formData.party_b || ''} onChange={(e) => update('party_b', e.target.value)} required />
          </Field>
          <Field label="Local Currency">
            <Input value={formData.local_currency || ''} onChange={(e) => update('local_currency', e.target.value.toUpperCase())} required />
          </Field>
          <Field label="Trade Date">
            <Input type="date" value={formData.trade_date || ''} onChange={(e) => update('trade_date', e.target.value)} required />
          </Field>
          <Field label="Effective Date">
            <Input type="date" value={formData.effective_date || ''} onChange={(e) => update('effective_date', e.target.value)} required />
          </Field>
          <Field label="Scheduled Termination Date">
            <Input
              type="date"
              value={formData.scheduled_termination_date || ''}
              onChange={(e) => update('scheduled_termination_date', e.target.value)}
              required
            />
          </Field>
          <Field label="Bond Return Payer">
            <Select
              value={formData.bond_return_payer}
              onValueChange={(value) => update('bond_return_payer', value as 'PartyA' | 'PartyB')}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PartyA">PartyA</SelectItem>
                <SelectItem value="PartyB">PartyB</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="Bond Return Receiver">
            <Select
              value={formData.bond_return_receiver}
              onValueChange={(value) => update('bond_return_receiver', value as 'PartyA' | 'PartyB')}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PartyA">PartyA</SelectItem>
                <SelectItem value="PartyB">PartyB</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="Notional Amount (Local)">
            <Input
              type="number"
              step="any"
              value={formData.notional_amount ?? ''}
              onChange={(e) => update('notional_amount', Number(e.target.value))}
              required
            />
          </Field>
          <Field label="USD Notional Amount">
            <Input
              type="number"
              step="any"
              value={formData.usd_notional_amount ?? ''}
              onChange={(e) => update('usd_notional_amount', Number(e.target.value))}
              required
            />
          </Field>
          <Field label="Initial Spot Rate">
            <Input
              type="number"
              step="any"
              value={formData.initial_spot_rate ?? ''}
              onChange={(e) => update('initial_spot_rate', Number(e.target.value))}
              required
            />
          </Field>
          <Field label="Current Market Price">
            <Input
              type="number"
              step="any"
              value={formData.current_market_price ?? ''}
              onChange={(e) => update('current_market_price', Number(e.target.value))}
              required
            />
          </Field>
          <Field label="Underlier">
            <Input value={formData.underlier || ''} onChange={(e) => update('underlier', e.target.value)} />
          </Field>
          <Field label="ISIN">
            <Input value={formData.isin || ''} onChange={(e) => update('isin', e.target.value)} />
          </Field>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit">Save</Button>
        </DialogFooter>
      </form>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      {children}
    </div>
  );
}
