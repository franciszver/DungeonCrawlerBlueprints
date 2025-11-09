# Frontend Tests

## Setup

Install test dependencies (already included in package.json):

```bash
npm install
```

## Running Tests

Run all tests:

```bash
npm test
```

Run tests in watch mode:

```bash
npm run test:watch
```

Run tests with coverage:

```bash
npm run test:coverage
```

## Test Structure

- `geometryHelpers.test.ts` - Tests for geometry utility functions
- `useRoomExtension.test.ts` - Tests for room extension hook
- `useUndoRedo.test.ts` - Tests for undo/redo functionality

## Writing Tests

Tests use Vitest and React Testing Library. Example:

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MyComponent from '../components/MyComponent';

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

## Mocking

Use Vitest's mocking utilities:

```typescript
import { vi } from 'vitest';

vi.mock('../services/api', () => ({
  getRoomSuggestions: vi.fn(),
}));
```

## Coverage Goals

- Unit tests: >80% coverage
- Component tests: Key user interactions covered
- Hook tests: All state transitions tested

