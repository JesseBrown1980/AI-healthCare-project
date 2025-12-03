/**
 * Chart Components
 * Data visualization components using Recharts
 * 
 * NOTE: Install recharts first: npm install recharts
 */

import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ComposedChart,
  Area,
} from 'recharts';
import type { RiskScores } from '../../api/types';
import './charts.css';

// ============================================================================
// Color Constants
// ============================================================================

const COLORS = {
  primary: '#3b82f6',
  secondary: '#6366f1',
  success: '#16a34a',
  warning: '#d97706',
  danger: '#dc2626',
  info: '#0284c7',
  gray: '#6b7280',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#d97706',
  low: '#65a30d',
  info: '#0284c7',
  unknown: '#6b7280',
};

const RISK_GRADIENT = [
  '#16a34a', // 0-20% - Green
  '#65a30d', // 20-40% - Light Green
  '#d97706', // 40-60% - Yellow/Orange
  '#ea580c', // 60-80% - Orange
  '#dc2626', // 80-100% - Red
];

// ============================================================================
// Risk Score Bar Chart
// ============================================================================

interface RiskScoreChartProps {
  riskScores: RiskScores;
  height?: number;
  showLabels?: boolean;
}

export const RiskScoreBarChart: React.FC<RiskScoreChartProps> = ({
  riskScores,
  height = 300,
  // showLabels is available but not currently used
}) => {
  const data = useMemo(() => {
    return Object.entries(riskScores)
      .filter(([_, value]) => value !== undefined && value !== null)
      .map(([key, value]) => ({
        name: formatRiskLabel(key),
        value: Math.round((value ?? 0) * 100),
        fill: getRiskColor((value ?? 0) * 100),
      }));
  }, [riskScores]);

  if (data.length === 0) {
    return <div className="chart-empty">No risk scores available</div>;
  }

  return (
    <div className="chart-container" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value: any) => [`${Number(value)}%`, 'Risk Score']}
            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ============================================================================
// Severity Distribution Pie Chart
// ============================================================================

interface SeverityDistributionProps {
  alerts: Array<{ severity?: string }>;
  height?: number;
  showLegend?: boolean;
}

export const SeverityDistributionChart: React.FC<SeverityDistributionProps> = ({
  alerts,
  height = 250,
  showLegend = true,
}) => {
  const data = useMemo(() => {
    const counts: Record<string, number> = {};
    alerts.forEach((alert) => {
      const severity = (alert.severity?.toLowerCase() ?? 'unknown') as string;
      counts[severity] = (counts[severity] || 0) + 1;
    });

    return Object.entries(counts).map(([severity, count]) => ({
      name: severity.charAt(0).toUpperCase() + severity.slice(1),
      value: count,
      color: SEVERITY_COLORS[severity] || SEVERITY_COLORS.unknown,
    }));
  }, [alerts]);

  if (data.length === 0) {
    return <div className="chart-empty">No alerts to display</div>;
  }

  return (
    <div className="chart-container" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
            label={({ name, percent }) => `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`}
            labelLine={false}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: any, name: any) => [Number(value), `${name} Alerts`]}
            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
          />
          {showLegend && <Legend />}
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

// ============================================================================
// Risk Radar Chart
// ============================================================================

interface RiskRadarChartProps {
  riskScores: RiskScores;
  height?: number;
}

export const RiskRadarChart: React.FC<RiskRadarChartProps> = ({ riskScores, height = 300 }) => {
  const data = useMemo(() => {
    return Object.entries(riskScores)
      .filter(([_, value]) => value !== undefined && value !== null)
      .map(([key, value]) => ({
        subject: formatRiskLabel(key),
        value: Math.round((value ?? 0) * 100),
        fullMark: 100,
      }));
  }, [riskScores]);

  if (data.length < 3) {
    return <div className="chart-empty">Not enough data for radar chart</div>;
  }

  return (
    <div className="chart-container" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
          <Radar
            name="Risk Score"
            dataKey="value"
            stroke={COLORS.primary}
            fill={COLORS.primary}
            fillOpacity={0.3}
          />
          <Tooltip
            formatter={(value: any) => [`${Number(value)}%`, 'Risk']}
            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ============================================================================
// Risk Gauge Component
// ============================================================================

interface RiskGaugeProps {
  value: number;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({ value, label, size = 'md' }) => {
  const percentage = Math.min(Math.max(value * 100, 0), 100);
  const color = getRiskColor(percentage);

  const sizes = {
    sm: { width: 80, strokeWidth: 6, fontSize: '0.875rem' },
    md: { width: 120, strokeWidth: 8, fontSize: '1.25rem' },
    lg: { width: 160, strokeWidth: 10, fontSize: '1.5rem' },
  };

  const { width, strokeWidth, fontSize } = sizes[size];
  const radius = (width - strokeWidth) / 2;
  // circumference calculation for future use
  // const circumference = radius * Math.PI; // Half circle
  // const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className="risk-gauge" style={{ width }}>
      <svg width={width} height={width / 2 + 20} viewBox={`0 0 ${width} ${width / 2 + 20}`}>
        {/* Background arc */}
        <path
          d={describeArc(width / 2, width / 2, radius, 180, 360)}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={describeArc(width / 2, width / 2, radius, 180, 180 + (percentage / 100) * 180)}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Value text */}
        <text
          x={width / 2}
          y={width / 2 - 5}
          textAnchor="middle"
          fontSize={fontSize}
          fontWeight="600"
          fill="#1f2937"
        >
          {Math.round(percentage)}%
        </text>
        {/* Label */}
        {label && (
          <text
            x={width / 2}
            y={width / 2 + 15}
            textAnchor="middle"
            fontSize="0.75rem"
            fill="#6b7280"
          >
            {label}
          </text>
        )}
      </svg>
    </div>
  );
};

// ============================================================================
// SHAP Waterfall Chart (for Explainability)
// ============================================================================

interface ShapValue {
  feature: string;
  value: number;
}

interface ShapWaterfallChartProps {
  shapValues: ShapValue[];
  baseValue?: number;
  height?: number;
}

export const ShapWaterfallChart: React.FC<ShapWaterfallChartProps> = ({
  shapValues,
  baseValue = 0.5,
  height = 400,
}) => {
  const data = useMemo(() => {
    // Sort by absolute value
    const sorted = [...shapValues].sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

    let cumulative = baseValue * 100;
    return sorted.map((item) => {
      const contribution = item.value * 100;
      const start = cumulative;
      cumulative += contribution;

      return {
        feature: formatFeatureName(item.feature),
        contribution: Math.abs(contribution),
        isPositive: contribution >= 0,
        start: Math.min(start, cumulative),
        end: Math.max(start, cumulative),
      };
    });
  }, [shapValues, baseValue]);

  return (
    <div className="chart-container" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 20, right: 30, left: 120, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <YAxis type="category" dataKey="feature" width={110} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(value: any, _name: any, props: any) => [
              `${props.payload.isPositive ? '+' : '-'}${Number(value).toFixed(1)}%`,
              'Contribution',
            ]}
            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
          />
          <Bar dataKey="contribution" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.isPositive ? COLORS.danger : COLORS.success} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ============================================================================
// Trend Line Chart
// ============================================================================

interface TrendDataPoint {
  date: string;
  value: number;
  label?: string;
}

interface TrendChartProps {
  data: TrendDataPoint[];
  height?: number;
  color?: string;
  showArea?: boolean;
}

export const TrendChart: React.FC<TrendChartProps> = ({
  data,
  height = 200,
  color = COLORS.primary,
  showArea = true,
}) => {
  if (data.length === 0) {
    return <div className="chart-empty">No trend data available</div>;
  }

  return (
    <div className="chart-container" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <Tooltip
            formatter={(value: any) => [`${Number(value)}%`, 'Value']}
            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
          />
          {showArea && (
            <Area type="monotone" dataKey="value" fill={color} fillOpacity={0.1} stroke="none" />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ fill: color, strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

// ============================================================================
// Mini Stat Card with Sparkline
// ============================================================================

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  trend?: number[];
  icon?: React.ReactNode;
}

export const StatCard: React.FC<StatCardProps> = ({ title, value, change, trend, icon }) => {
  const isPositive = change !== undefined && change >= 0;

  return (
    <div className="stat-card">
      <div className="stat-card__header">
        {icon && <div className="stat-card__icon">{icon}</div>}
        <span className="stat-card__title">{title}</span>
      </div>
      <div className="stat-card__value">{value}</div>
      {change !== undefined && (
        <div className={`stat-card__change ${isPositive ? 'stat-card__change--positive' : 'stat-card__change--negative'}`}>
          {isPositive ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
        </div>
      )}
      {trend && trend.length > 0 && (
        <div className="stat-card__sparkline">
          <ResponsiveContainer width="100%" height={30}>
            <LineChart data={trend.map((v, i) => ({ value: v, index: i }))}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={isPositive ? COLORS.success : COLORS.danger}
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Helper Functions
// ============================================================================

function formatRiskLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/risk$/i, '')
    .trim()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatFeatureName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

function getRiskColor(percentage: number): string {
  if (percentage < 20) return RISK_GRADIENT[0];
  if (percentage < 40) return RISK_GRADIENT[1];
  if (percentage < 60) return RISK_GRADIENT[2];
  if (percentage < 80) return RISK_GRADIENT[3];
  return RISK_GRADIENT[4];
}

function polarToCartesian(centerX: number, centerY: number, radius: number, angleInDegrees: number) {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  };
}

function describeArc(x: number, y: number, radius: number, startAngle: number, endAngle: number): string {
  const start = polarToCartesian(x, y, radius, endAngle);
  const end = polarToCartesian(x, y, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
}
