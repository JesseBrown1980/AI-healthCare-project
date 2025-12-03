/**
 * Utility Functions Tests
 */

import { describe, it, expect } from 'vitest';
import {
  formatDate,
  formatPercentage,
  truncate,
  capitalize,
  isValidEmail,
  debounce,
  getSeverityColor,
  getSeverityFromScore,
} from '../../utils';

describe('formatDate', () => {
  it('formats date correctly', () => {
    const date = new Date('2024-01-15T10:30:00Z');
    const result = formatDate(date);
    expect(result).toBeDefined();
    expect(typeof result).toBe('string');
  });

  it('handles string input', () => {
    const result = formatDate('2024-01-15');
    expect(result).toBeDefined();
  });

  it('returns Invalid Date for invalid date', () => {
    const result = formatDate('invalid');
    expect(result).toBe('Invalid Date');
  });

  it('returns N/A for null', () => {
    const result = formatDate(null);
    expect(result).toBe('N/A');
  });
});

describe('formatPercentage', () => {
  it('formats percentage correctly', () => {
    expect(formatPercentage(0.75)).toBe('75%');
  });

  it('handles decimals', () => {
    expect(formatPercentage(0.756, 1)).toBe('75.6%');
  });

  it('handles zero', () => {
    expect(formatPercentage(0)).toBe('0%');
  });

  it('returns N/A for null', () => {
    expect(formatPercentage(null)).toBe('N/A');
  });
});

describe('truncate', () => {
  it('truncates long text', () => {
    const text = 'This is a very long text that should be truncated';
    expect(truncate(text, 20)).toBe('This is a very lo...');
  });

  it('does not truncate short text', () => {
    const text = 'Short';
    expect(truncate(text, 20)).toBe('Short');
  });

  it('handles empty string', () => {
    expect(truncate('', 20)).toBe('');
  });
});

describe('capitalize', () => {
  it('capitalizes first letter', () => {
    expect(capitalize('hello')).toBe('Hello');
  });

  it('handles empty string', () => {
    expect(capitalize('')).toBe('');
  });

  it('lowercases rest of string', () => {
    expect(capitalize('HELLO')).toBe('Hello');
  });
});

describe('isValidEmail', () => {
  it('validates correct email', () => {
    expect(isValidEmail('test@example.com')).toBe(true);
  });

  it('rejects invalid email', () => {
    expect(isValidEmail('invalid')).toBe(false);
    expect(isValidEmail('test@')).toBe(false);
    expect(isValidEmail('@example.com')).toBe(false);
  });
});

describe('debounce', () => {
  it('debounces function calls', async () => {
    let callCount = 0;
    const fn = () => { callCount++; };
    const debouncedFn = debounce(fn, 100);

    debouncedFn();
    debouncedFn();
    debouncedFn();

    expect(callCount).toBe(0);

    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(callCount).toBe(1);
  });
});

describe('getSeverityColor', () => {
  it('returns correct colors for severities', () => {
    expect(getSeverityColor('critical')).toBe('#dc2626');
    expect(getSeverityColor('high')).toBe('#ea580c');
    expect(getSeverityColor('medium')).toBe('#d97706');
    expect(getSeverityColor('low')).toBe('#65a30d');
    expect(getSeverityColor('info')).toBe('#0284c7');
  });
});

describe('getSeverityFromScore', () => {
  it('returns correct severity levels', () => {
    expect(getSeverityFromScore(0.9)).toBe('critical');
    expect(getSeverityFromScore(0.7)).toBe('high');
    expect(getSeverityFromScore(0.5)).toBe('medium');
    expect(getSeverityFromScore(0.3)).toBe('low');
    expect(getSeverityFromScore(0.1)).toBe('info');
  });
});
