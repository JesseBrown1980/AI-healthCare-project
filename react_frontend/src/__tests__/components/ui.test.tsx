/**
 * UI Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
  SeverityBadge,
  Input,
  Select,
  EmptyState,
} from '../../components/ui';

describe('Card Components', () => {
  it('renders Card with children', () => {
    render(<Card>Card Content</Card>);
    expect(screen.getByText('Card Content')).toBeInTheDocument();
  });

  it('renders CardHeader with title and description', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Title</CardTitle>
          <CardDescription>Test Description</CardDescription>
        </CardHeader>
      </Card>
    );
    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
  });

  it('renders CardContent', () => {
    render(
      <Card>
        <CardContent>Content Here</CardContent>
      </Card>
    );
    expect(screen.getByText('Content Here')).toBeInTheDocument();
  });
});

describe('Button', () => {
  it('renders button with text', () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByRole('button', { name: 'Click Me' })).toBeInTheDocument();
  });

  it('handles click events', () => {
    let clicked = false;
    render(<Button onClick={() => { clicked = true; }}>Click</Button>);
    fireEvent.click(screen.getByRole('button'));
    expect(clicked).toBe(true);
  });

  it('can be disabled', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});

describe('Badge', () => {
  it('renders badge with text', () => {
    render(<Badge>Status</Badge>);
    expect(screen.getByText('Status')).toBeInTheDocument();
  });
});

describe('SeverityBadge', () => {
  it('renders severity badge', () => {
    render(<SeverityBadge severity="critical" />);
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('handles different severities', () => {
    const { rerender } = render(<SeverityBadge severity="high" />);
    expect(screen.getByText('High')).toBeInTheDocument();

    rerender(<SeverityBadge severity="medium" />);
    expect(screen.getByText('Medium')).toBeInTheDocument();

    rerender(<SeverityBadge severity="low" />);
    expect(screen.getByText('Low')).toBeInTheDocument();
  });
});

describe('Input', () => {
  it('renders input', () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  it('handles value changes', () => {
    let value = '';
    render(
      <Input
        value={value}
        onChange={(e) => { value = e.target.value; }}
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test' } });
    expect(value).toBe('test');
  });

  it('can be disabled', () => {
    render(<Input disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });
});

describe('Select', () => {
  const options = [
    { value: 'a', label: 'Option A' },
    { value: 'b', label: 'Option B' },
    { value: 'c', label: 'Option C' },
  ];

  it('renders select with options', () => {
    render(<Select options={options} value="a" onChange={() => {}} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('handles selection changes', () => {
    let selected = 'a';
    render(
      <Select
        options={options}
        value={selected}
        onChange={(v) => { selected = v; }}
      />
    );
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'b' } });
    expect(selected).toBe('b');
  });
});

describe('EmptyState', () => {
  it('renders empty state with title and description', () => {
    render(
      <EmptyState
        title="No Data"
        description="There is no data to display"
      />
    );
    expect(screen.getByText('No Data')).toBeInTheDocument();
    expect(screen.getByText('There is no data to display')).toBeInTheDocument();
  });

  it('renders with action', () => {
    render(
      <EmptyState
        title="No Data"
        description="There is no data"
        action={<Button>Add Data</Button>}
      />
    );
    expect(screen.getByRole('button', { name: 'Add Data' })).toBeInTheDocument();
  });
});
