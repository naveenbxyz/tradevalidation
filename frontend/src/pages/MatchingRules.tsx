import { useEffect, useState } from 'react';
import { Plus, Save, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { MatchingRule } from '@/types/trade';

const API_BASE = 'http://localhost:8000';

const TRS_FIELDS = [
  'trade_id',
  'party_a',
  'party_b',
  'trade_date',
  'effective_date',
  'scheduled_termination_date',
  'bond_return_payer',
  'bond_return_receiver',
  'local_currency',
  'notional_amount',
  'usd_notional_amount',
  'initial_spot_rate',
  'current_market_price',
  'underlier',
  'isin',
];

export function MatchingRules() {
  const [rules, setRules] = useState<MatchingRule[]>([]);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/rules`);
      if (response.ok) {
        const data = await response.json();
        if (data.length > 0) {
          setRules(data);
          return;
        }
      }
      initializeDefaultRules();
    } catch {
      initializeDefaultRules();
    }
  };

  const initializeDefaultRules = () => {
    const defaults: MatchingRule[] = TRS_FIELDS.map((field, index) => ({
      id: `trs-${index}`,
      field_name: field,
      rule_type: defaultRuleType(field),
      tolerance_value: defaultTolerance(field),
      tolerance_unit: defaultToleranceUnit(field),
      min_confidence: defaultMinConfidence(field),
      enabled: true,
    }));
    setRules(defaults);
  };

  const defaultRuleType = (field: string): MatchingRule['rule_type'] => {
    if (field.includes('date')) return 'date_tolerance';
    if (['notional_amount', 'usd_notional_amount', 'initial_spot_rate', 'current_market_price'].includes(field)) {
      return 'tolerance';
    }
    if (['party_a', 'party_b', 'underlier'].includes(field)) return 'fuzzy';
    return 'exact';
  };

  const defaultTolerance = (field: string): number | undefined => {
    if (field.includes('date')) return 1;
    if (field.includes('notional')) return 0.1;
    if (field === 'initial_spot_rate') return 0.001;
    if (field === 'current_market_price') return 0.25;
    return undefined;
  };

  const defaultToleranceUnit = (field: string): MatchingRule['tolerance_unit'] | undefined => {
    if (field.includes('date')) return 'days';
    if (field.includes('notional')) return 'percent';
    if (field === 'initial_spot_rate' || field === 'current_market_price') return 'absolute';
    return undefined;
  };

  const defaultMinConfidence = (field: string): number => {
    if (['bond_return_payer', 'bond_return_receiver', 'local_currency'].includes(field)) return 0.9;
    if (field.includes('date') || field.includes('notional')) return 0.85;
    if (['party_a', 'party_b'].includes(field)) return 0.8;
    return 0.7;
  };

  const updateRule = (id: string, updates: Partial<MatchingRule>) => {
    setRules((prev) => prev.map((rule) => (rule.id === id ? { ...rule, ...updates } : rule)));
    setHasChanges(true);
  };

  const addCustomRule = () => {
    setRules((prev) => [
      ...prev,
      {
        id: `custom-${Date.now()}`,
        field_name: '',
        rule_type: 'exact',
        min_confidence: 0.7,
        enabled: true,
      },
    ]);
    setHasChanges(true);
  };

  const deleteRule = (id: string) => {
    setRules((prev) => prev.filter((rule) => rule.id !== id));
    setHasChanges(true);
  };

  const saveRules = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/rules`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rules),
      });
      if (response.ok) {
        setHasChanges(false);
      }
    } catch (error) {
      console.error('Failed to save rules:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">TRS Matching Rules</h1>
          <p className="text-muted-foreground">Configure field-level matching type, tolerance, and confidence requirement.</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={addCustomRule}>
            <Plus className="mr-2 h-4 w-4" />
            Add Rule
          </Button>
          <Button onClick={saveRules} disabled={!hasChanges}>
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Field Rules</CardTitle>
          <CardDescription>Rules apply during validation before checker review.</CardDescription>
        </CardHeader>
        <CardContent>
          <RulesList rules={rules} onUpdate={updateRule} onDelete={deleteRule} />
        </CardContent>
      </Card>
    </div>
  );
}

interface RulesListProps {
  rules: MatchingRule[];
  onUpdate: (id: string, updates: Partial<MatchingRule>) => void;
  onDelete: (id: string) => void;
}

function RulesList({ rules, onUpdate, onDelete }: RulesListProps) {
  return (
    <div className="space-y-4">
      {rules.map((rule) => (
        <div key={rule.id} className="flex items-center space-x-4 p-4 border rounded-lg">
          <Switch checked={rule.enabled} onCheckedChange={(checked) => onUpdate(rule.id, { enabled: checked })} />

          <div className="flex-1 grid grid-cols-5 gap-4">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Field</Label>
              <Input
                value={rule.field_name}
                onChange={(e) => onUpdate(rule.id, { field_name: e.target.value })}
                className="h-8"
                disabled={!rule.id.startsWith('custom-')}
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Rule Type</Label>
              <Select
                value={rule.rule_type}
                onValueChange={(value) => onUpdate(rule.id, { rule_type: value as MatchingRule['rule_type'] })}
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="exact">Exact</SelectItem>
                  <SelectItem value="tolerance">Tolerance</SelectItem>
                  <SelectItem value="fuzzy">Fuzzy</SelectItem>
                  <SelectItem value="date_tolerance">Date Tolerance</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Tolerance</Label>
              <Input
                type="number"
                step="any"
                className="h-8"
                value={rule.tolerance_value ?? ''}
                onChange={(e) => onUpdate(rule.id, { tolerance_value: Number(e.target.value) || undefined })}
                disabled={rule.rule_type !== 'tolerance' && rule.rule_type !== 'date_tolerance'}
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Unit</Label>
              <Select
                value={rule.tolerance_unit || 'absolute'}
                onValueChange={(value) => onUpdate(rule.id, { tolerance_unit: value as MatchingRule['tolerance_unit'] })}
                disabled={rule.rule_type !== 'tolerance' && rule.rule_type !== 'date_tolerance'}
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="absolute">Absolute</SelectItem>
                  <SelectItem value="percent">Percent</SelectItem>
                  <SelectItem value="days">Days</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Min Confidence</Label>
              <Input
                type="number"
                min={0}
                max={1}
                step="0.01"
                className="h-8"
                value={rule.min_confidence}
                onChange={(e) => onUpdate(rule.id, { min_confidence: Number(e.target.value) })}
              />
            </div>
          </div>

          <Button variant="ghost" size="icon" onClick={() => onDelete(rule.id)}>
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      ))}
    </div>
  );
}
