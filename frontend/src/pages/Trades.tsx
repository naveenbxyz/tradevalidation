import { useState, useEffect } from 'react';
import { Plus, Pencil, Trash2, Download, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { FXTrade, SwapTrade } from '@/types/trade';

const API_BASE = 'http://localhost:8000';

export function Trades() {
  const [fxTrades, setFxTrades] = useState<FXTrade[]>([]);
  const [swapTrades, setSwapTrades] = useState<SwapTrade[]>([]);
  const [editingFX, setEditingFX] = useState<FXTrade | null>(null);
  const [editingSwap, setEditingSwap] = useState<SwapTrade | null>(null);
  const [isAddingFX, setIsAddingFX] = useState(false);
  const [isAddingSwap, setIsAddingSwap] = useState(false);

  useEffect(() => {
    fetchTrades();
  }, []);

  const fetchTrades = async () => {
    try {
      const [fxRes, swapRes] = await Promise.all([
        fetch(`${API_BASE}/api/trades/fx`),
        fetch(`${API_BASE}/api/trades/swap`),
      ]);

      if (fxRes.ok) setFxTrades(await fxRes.json());
      if (swapRes.ok) setSwapTrades(await swapRes.json());
    } catch (error) {
      console.error('Failed to fetch trades:', error);
    }
  };

  const saveFXTrade = async (trade: Partial<FXTrade>) => {
    try {
      const url = trade.id
        ? `${API_BASE}/api/trades/fx/${trade.id}`
        : `${API_BASE}/api/trades/fx`;
      const method = trade.id ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trade),
      });

      if (response.ok) {
        await fetchTrades();
        setEditingFX(null);
        setIsAddingFX(false);
      }
    } catch (error) {
      console.error('Failed to save FX trade:', error);
    }
  };

  const saveSwapTrade = async (trade: Partial<SwapTrade>) => {
    try {
      const url = trade.id
        ? `${API_BASE}/api/trades/swap/${trade.id}`
        : `${API_BASE}/api/trades/swap`;
      const method = trade.id ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trade),
      });

      if (response.ok) {
        await fetchTrades();
        setEditingSwap(null);
        setIsAddingSwap(false);
      }
    } catch (error) {
      console.error('Failed to save Swap trade:', error);
    }
  };

  const deleteFXTrade = async (id: string) => {
    try {
      await fetch(`${API_BASE}/api/trades/fx/${id}`, { method: 'DELETE' });
      await fetchTrades();
    } catch (error) {
      console.error('Failed to delete FX trade:', error);
    }
  };

  const deleteSwapTrade = async (id: string) => {
    try {
      await fetch(`${API_BASE}/api/trades/swap/${id}`, { method: 'DELETE' });
      await fetchTrades();
    } catch (error) {
      console.error('Failed to delete Swap trade:', error);
    }
  };

  const exportTrades = () => {
    const data = { fx_trades: fxTrades, swap_trades: swapTrades };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'system_trades.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const importTrades = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const text = await file.text();
    const data = JSON.parse(text);

    try {
      await fetch(`${API_BASE}/api/trades/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      await fetchTrades();
    } catch (error) {
      console.error('Failed to import trades:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Trades</h1>
          <p className="text-muted-foreground">
            Internal trade records received into the validation system
          </p>
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
              <input
                type="file"
                className="hidden"
                accept=".json"
                onChange={importTrades}
              />
            </label>
          </Button>
        </div>
      </div>

      <Tabs defaultValue="fx" className="space-y-4">
        <TabsList>
          <TabsTrigger value="fx">FX Trades ({fxTrades.length})</TabsTrigger>
          <TabsTrigger value="swap">Swap Trades ({swapTrades.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="fx">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>FX Trades</CardTitle>
                <CardDescription>
                  Foreign exchange spot and forward trades
                </CardDescription>
              </div>
              <Dialog open={isAddingFX} onOpenChange={setIsAddingFX}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add FX Trade
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <FXTradeForm
                    onSave={saveFXTrade}
                    onCancel={() => setIsAddingFX(false)}
                  />
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Trade ID</TableHead>
                    <TableHead>Counterparty</TableHead>
                    <TableHead>Currency Pair</TableHead>
                    <TableHead>Direction</TableHead>
                    <TableHead>Notional</TableHead>
                    <TableHead>Rate</TableHead>
                    <TableHead>Trade Date</TableHead>
                    <TableHead>Value Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fxTrades.map((trade) => (
                    <TableRow key={trade.id}>
                      <TableCell className="font-mono">{trade.trade_id}</TableCell>
                      <TableCell>{trade.counterparty}</TableCell>
                      <TableCell>{trade.currency_pair}</TableCell>
                      <TableCell>
                        <Badge variant={trade.direction === 'BUY' ? 'default' : 'secondary'}>
                          {trade.direction}
                        </Badge>
                      </TableCell>
                      <TableCell>{trade.notional.toLocaleString()}</TableCell>
                      <TableCell>{trade.rate}</TableCell>
                      <TableCell>{trade.trade_date}</TableCell>
                      <TableCell>{trade.value_date}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end space-x-2">
                          <Dialog open={editingFX?.id === trade.id} onOpenChange={(open) => !open && setEditingFX(null)}>
                            <DialogTrigger asChild>
                              <Button variant="ghost" size="icon" onClick={() => setEditingFX(trade)}>
                                <Pencil className="h-4 w-4" />
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-2xl">
                              <FXTradeForm
                                trade={trade}
                                onSave={saveFXTrade}
                                onCancel={() => setEditingFX(null)}
                              />
                            </DialogContent>
                          </Dialog>
                          <Button variant="ghost" size="icon" onClick={() => deleteFXTrade(trade.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {fxTrades.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                        No FX trades found. Add one to get started.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="swap">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Swap Trades</CardTitle>
                <CardDescription>
                  Interest rate swaps and cross-currency swaps
                </CardDescription>
              </div>
              <Dialog open={isAddingSwap} onOpenChange={setIsAddingSwap}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Swap Trade
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <SwapTradeForm
                    onSave={saveSwapTrade}
                    onCancel={() => setIsAddingSwap(false)}
                  />
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Trade ID</TableHead>
                    <TableHead>Counterparty</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Notional</TableHead>
                    <TableHead>Fixed Rate</TableHead>
                    <TableHead>Float Index</TableHead>
                    <TableHead>Effective</TableHead>
                    <TableHead>Maturity</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {swapTrades.map((trade) => (
                    <TableRow key={trade.id}>
                      <TableCell className="font-mono">{trade.trade_id}</TableCell>
                      <TableCell>{trade.counterparty}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{trade.trade_type}</Badge>
                      </TableCell>
                      <TableCell>{trade.notional.toLocaleString()} {trade.currency}</TableCell>
                      <TableCell>{trade.fixed_rate}%</TableCell>
                      <TableCell>{trade.floating_index}</TableCell>
                      <TableCell>{trade.effective_date}</TableCell>
                      <TableCell>{trade.maturity_date}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end space-x-2">
                          <Dialog open={editingSwap?.id === trade.id} onOpenChange={(open) => !open && setEditingSwap(null)}>
                            <DialogTrigger asChild>
                              <Button variant="ghost" size="icon" onClick={() => setEditingSwap(trade)}>
                                <Pencil className="h-4 w-4" />
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-2xl">
                              <SwapTradeForm
                                trade={trade}
                                onSave={saveSwapTrade}
                                onCancel={() => setEditingSwap(null)}
                              />
                            </DialogContent>
                          </Dialog>
                          <Button variant="ghost" size="icon" onClick={() => deleteSwapTrade(trade.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {swapTrades.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                        No swap trades found. Add one to get started.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

interface FXTradeFormProps {
  trade?: FXTrade;
  onSave: (trade: Partial<FXTrade>) => void;
  onCancel: () => void;
}

function FXTradeForm({ trade, onSave, onCancel }: FXTradeFormProps) {
  const [form, setForm] = useState<Partial<FXTrade>>(trade || {
    trade_id: '',
    counterparty: '',
    currency_pair: 'EUR/USD',
    direction: 'BUY',
    notional: 0,
    rate: 0,
    trade_date: new Date().toISOString().split('T')[0],
    value_date: new Date().toISOString().split('T')[0],
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(form);
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>{trade ? 'Edit FX Trade' : 'Add FX Trade'}</DialogTitle>
        <DialogDescription>
          Enter the trade details below
        </DialogDescription>
      </DialogHeader>
      <div className="grid grid-cols-2 gap-4 py-4">
        <div className="space-y-2">
          <Label htmlFor="trade_id">Trade ID</Label>
          <Input
            id="trade_id"
            value={form.trade_id}
            onChange={(e) => setForm({ ...form, trade_id: e.target.value })}
            placeholder="FX-2024-001"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="counterparty">Counterparty</Label>
          <Input
            id="counterparty"
            value={form.counterparty}
            onChange={(e) => setForm({ ...form, counterparty: e.target.value })}
            placeholder="Goldman Sachs"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="currency_pair">Currency Pair</Label>
          <Select
            value={form.currency_pair}
            onValueChange={(value) => setForm({ ...form, currency_pair: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="EUR/USD">EUR/USD</SelectItem>
              <SelectItem value="GBP/USD">GBP/USD</SelectItem>
              <SelectItem value="USD/JPY">USD/JPY</SelectItem>
              <SelectItem value="USD/CHF">USD/CHF</SelectItem>
              <SelectItem value="AUD/USD">AUD/USD</SelectItem>
              <SelectItem value="USD/CAD">USD/CAD</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="direction">Direction</Label>
          <Select
            value={form.direction}
            onValueChange={(value) => setForm({ ...form, direction: value as 'BUY' | 'SELL' })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="BUY">BUY</SelectItem>
              <SelectItem value="SELL">SELL</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="notional">Notional</Label>
          <Input
            id="notional"
            type="number"
            value={form.notional}
            onChange={(e) => setForm({ ...form, notional: parseFloat(e.target.value) })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="rate">Rate</Label>
          <Input
            id="rate"
            type="number"
            step="0.0001"
            value={form.rate}
            onChange={(e) => setForm({ ...form, rate: parseFloat(e.target.value) })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="trade_date">Trade Date</Label>
          <Input
            id="trade_date"
            type="date"
            value={form.trade_date}
            onChange={(e) => setForm({ ...form, trade_date: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="value_date">Value Date</Label>
          <Input
            id="value_date"
            type="date"
            value={form.value_date}
            onChange={(e) => setForm({ ...form, value_date: e.target.value })}
          />
        </div>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save</Button>
      </DialogFooter>
    </form>
  );
}

interface SwapTradeFormProps {
  trade?: SwapTrade;
  onSave: (trade: Partial<SwapTrade>) => void;
  onCancel: () => void;
}

function SwapTradeForm({ trade, onSave, onCancel }: SwapTradeFormProps) {
  const [form, setForm] = useState<Partial<SwapTrade>>(trade || {
    trade_id: '',
    counterparty: '',
    trade_type: 'IRS',
    notional: 0,
    currency: 'USD',
    fixed_rate: 0,
    floating_index: 'SOFR',
    spread: 0,
    effective_date: new Date().toISOString().split('T')[0],
    maturity_date: new Date().toISOString().split('T')[0],
    payment_frequency: 'Quarterly',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(form);
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>{trade ? 'Edit Swap Trade' : 'Add Swap Trade'}</DialogTitle>
        <DialogDescription>
          Enter the swap trade details below
        </DialogDescription>
      </DialogHeader>
      <div className="grid grid-cols-2 gap-4 py-4">
        <div className="space-y-2">
          <Label htmlFor="trade_id">Trade ID</Label>
          <Input
            id="trade_id"
            value={form.trade_id}
            onChange={(e) => setForm({ ...form, trade_id: e.target.value })}
            placeholder="IRS-2024-001"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="counterparty">Counterparty</Label>
          <Input
            id="counterparty"
            value={form.counterparty}
            onChange={(e) => setForm({ ...form, counterparty: e.target.value })}
            placeholder="JP Morgan"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="trade_type">Trade Type</Label>
          <Select
            value={form.trade_type}
            onValueChange={(value) => setForm({ ...form, trade_type: value as 'IRS' | 'CCS' | 'BASIS' })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="IRS">Interest Rate Swap (IRS)</SelectItem>
              <SelectItem value="CCS">Cross Currency Swap (CCS)</SelectItem>
              <SelectItem value="BASIS">Basis Swap</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="currency">Currency</Label>
          <Select
            value={form.currency}
            onValueChange={(value) => setForm({ ...form, currency: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="USD">USD</SelectItem>
              <SelectItem value="EUR">EUR</SelectItem>
              <SelectItem value="GBP">GBP</SelectItem>
              <SelectItem value="JPY">JPY</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="notional">Notional</Label>
          <Input
            id="notional"
            type="number"
            value={form.notional}
            onChange={(e) => setForm({ ...form, notional: parseFloat(e.target.value) })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="fixed_rate">Fixed Rate (%)</Label>
          <Input
            id="fixed_rate"
            type="number"
            step="0.01"
            value={form.fixed_rate}
            onChange={(e) => setForm({ ...form, fixed_rate: parseFloat(e.target.value) })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="floating_index">Floating Index</Label>
          <Select
            value={form.floating_index}
            onValueChange={(value) => setForm({ ...form, floating_index: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="SOFR">SOFR</SelectItem>
              <SelectItem value="EURIBOR">EURIBOR</SelectItem>
              <SelectItem value="SONIA">SONIA</SelectItem>
              <SelectItem value="TONAR">TONAR</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="spread">Spread (%)</Label>
          <Input
            id="spread"
            type="number"
            step="0.01"
            value={form.spread}
            onChange={(e) => setForm({ ...form, spread: parseFloat(e.target.value) })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="effective_date">Effective Date</Label>
          <Input
            id="effective_date"
            type="date"
            value={form.effective_date}
            onChange={(e) => setForm({ ...form, effective_date: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="maturity_date">Maturity Date</Label>
          <Input
            id="maturity_date"
            type="date"
            value={form.maturity_date}
            onChange={(e) => setForm({ ...form, maturity_date: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="payment_frequency">Payment Frequency</Label>
          <Select
            value={form.payment_frequency}
            onValueChange={(value) => setForm({ ...form, payment_frequency: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Monthly">Monthly</SelectItem>
              <SelectItem value="Quarterly">Quarterly</SelectItem>
              <SelectItem value="Semi-Annual">Semi-Annual</SelectItem>
              <SelectItem value="Annual">Annual</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save</Button>
      </DialogFooter>
    </form>
  );
}
