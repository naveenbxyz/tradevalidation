import { useState, useEffect } from 'react';
import { Plus, Trash2, Save } from 'lucide-react';
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

const DEFAULT_FX_FIELDS = [
  'trade_id',
  'counterparty',
  'currency_pair',
  'direction',
  'notional',
  'rate',
  'trade_date',
  'value_date',
];

const DEFAULT_SWAP_FIELDS = [
  'trade_id',
  'counterparty',
  'trade_type',
  'notional',
  'currency',
  'fixed_rate',
  'floating_index',
  'spread',
  'effective_date',
  'maturity_date',
  'payment_frequency',
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
        setRules(data);
      } else {
        // Initialize with default rules if none exist
        initializeDefaultRules();
      }
    } catch (error) {
      console.error('Failed to fetch rules:', error);
      initializeDefaultRules();
    }
  };

  const initializeDefaultRules = () => {
    const defaultRules: MatchingRule[] = [
      ...DEFAULT_FX_FIELDS.map((field, index) => ({
        id: `fx-${index}`,
        field_name: field,
        rule_type: getDefaultRuleType(field) as MatchingRule['rule_type'],
        tolerance_value: getDefaultTolerance(field),
        tolerance_unit: getDefaultToleranceUnit(field) as MatchingRule['tolerance_unit'],
        enabled: true,
      })),
      ...DEFAULT_SWAP_FIELDS.map((field, index) => ({
        id: `swap-${index}`,
        field_name: field,
        rule_type: getDefaultRuleType(field) as MatchingRule['rule_type'],
        tolerance_value: getDefaultTolerance(field),
        tolerance_unit: getDefaultToleranceUnit(field) as MatchingRule['tolerance_unit'],
        enabled: true,
      })),
    ];
    setRules(defaultRules);
  };

  const getDefaultRuleType = (field: string): string => {
    if (field.includes('date')) return 'date_tolerance';
    if (field === 'rate' || field === 'fixed_rate' || field === 'spread') return 'tolerance';
    if (field === 'notional') return 'tolerance';
    if (field === 'counterparty') return 'fuzzy';
    return 'exact';
  };

  const getDefaultTolerance = (field: string): number => {
    if (field.includes('date')) return 1;
    if (field === 'rate' || field === 'fixed_rate') return 0.01;
    if (field === 'spread') return 0.01;
    if (field === 'notional') return 0.01;
    return 0;
  };

  const getDefaultToleranceUnit = (field: string): string => {
    if (field.includes('date')) return 'days';
    if (field === 'notional') return 'percent';
    return 'absolute';
  };

  const updateRule = (id: string, updates: Partial<MatchingRule>) => {
    setRules(rules.map(rule =>
      rule.id === id ? { ...rule, ...updates } : rule
    ));
    setHasChanges(true);
  };

  const addRule = () => {
    const newRule: MatchingRule = {
      id: `custom-${Date.now()}`,
      field_name: '',
      rule_type: 'exact',
      enabled: true,
    };
    setRules([...rules, newRule]);
    setHasChanges(true);
  };

  const deleteRule = (id: string) => {
    setRules(rules.filter(rule => rule.id !== id));
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

  const fxRules = rules.filter(r => r.id.startsWith('fx-') || DEFAULT_FX_FIELDS.includes(r.field_name));
  const swapRules = rules.filter(r => r.id.startsWith('swap-') || DEFAULT_SWAP_FIELDS.includes(r.field_name));
  const customRules = rules.filter(r => r.id.startsWith('custom-'));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Matching Rules</h1>
          <p className="text-muted-foreground">
            Configure how fields are compared during validation
          </p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={addRule}>
            <Plus className="mr-2 h-4 w-4" />
            Add Rule
          </Button>
          <Button onClick={saveRules} disabled={!hasChanges}>
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </Button>
        </div>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>FX Trade Rules</CardTitle>
            <CardDescription>
              Matching rules for foreign exchange trades
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RulesList
              rules={fxRules}
              onUpdate={updateRule}
              onDelete={deleteRule}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Swap Trade Rules</CardTitle>
            <CardDescription>
              Matching rules for interest rate and currency swaps
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RulesList
              rules={swapRules}
              onUpdate={updateRule}
              onDelete={deleteRule}
            />
          </CardContent>
        </Card>

        {customRules.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Custom Rules</CardTitle>
              <CardDescription>
                User-defined matching rules
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RulesList
                rules={customRules}
                onUpdate={updateRule}
                onDelete={deleteRule}
                allowDelete
              />
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Rule Types Reference</CardTitle>
          <CardDescription>
            Understanding different matching strategies
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold mb-2">Exact Match</h4>
              <p className="text-sm text-muted-foreground">
                Values must be identical. Best for IDs, directions, and categorical fields.
              </p>
            </div>
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold mb-2">Tolerance</h4>
              <p className="text-sm text-muted-foreground">
                Allows small differences. Use for rates (e.g., +/- 0.0001) or notionals (e.g., +/- 0.01%).
              </p>
            </div>
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold mb-2">Fuzzy Match</h4>
              <p className="text-sm text-muted-foreground">
                Uses string similarity. Good for counterparty names with slight variations.
              </p>
            </div>
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold mb-2">Date Tolerance</h4>
              <p className="text-sm text-muted-foreground">
                Allows date differences in days. Useful for T+1/T+2 flexibility on settlement dates.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface RulesListProps {
  rules: MatchingRule[];
  onUpdate: (id: string, updates: Partial<MatchingRule>) => void;
  onDelete: (id: string) => void;
  allowDelete?: boolean;
}

function RulesList({ rules, onUpdate, onDelete, allowDelete }: RulesListProps) {
  return (
    <div className="space-y-4">
      {rules.map((rule) => (
        <div
          key={rule.id}
          className="flex items-center space-x-4 p-4 border rounded-lg"
        >
          <Switch
            checked={rule.enabled}
            onCheckedChange={(checked) => onUpdate(rule.id, { enabled: checked })}
          />

          <div className="flex-1 grid grid-cols-4 gap-4">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Field Name</Label>
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

            {(rule.rule_type === 'tolerance' || rule.rule_type === 'date_tolerance') && (
              <>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Tolerance</Label>
                  <Input
                    type="number"
                    step={rule.rule_type === 'date_tolerance' ? '1' : '0.0001'}
                    value={rule.tolerance_value || 0}
                    onChange={(e) => onUpdate(rule.id, { tolerance_value: parseFloat(e.target.value) })}
                    className="h-8"
                  />
                </div>

                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Unit</Label>
                  <Select
                    value={rule.tolerance_unit || 'absolute'}
                    onValueChange={(value) => onUpdate(rule.id, { tolerance_unit: value as MatchingRule['tolerance_unit'] })}
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {rule.rule_type === 'date_tolerance' ? (
                        <SelectItem value="days">Days</SelectItem>
                      ) : (
                        <>
                          <SelectItem value="absolute">Absolute</SelectItem>
                          <SelectItem value="percent">Percent</SelectItem>
                        </>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}
          </div>

          {allowDelete && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(rule.id)}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          )}
        </div>
      ))}

      {rules.length === 0 && (
        <div className="text-center text-muted-foreground py-8">
          No rules configured. Click "Add Rule" to create one.
        </div>
      )}
    </div>
  );
}
