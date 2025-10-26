# Julee Example UI

A minimal responsive Single Page Application (SPA) built with Vite, React, TypeScript, and Tailwind CSS to demo the Julee Example workflow system for Capture, Extract, Assemble, and Publish operations.

It currently just displays the dashboard, but the aim is to support
defining and running assemblies (consultant workflows (?)).

## 🚀 Features

- **Stack**: Vite + React 18, TypeScript, Tailwind CSS 4
- **Component Library**: shadcn/ui components with Radix UI primitives
- **Type Safety**: Full TypeScript support with strict type checking
- **Testing**: Vitest for unit tests with coverage reporting
- **API Integration**: Axios-based client for FastAPI backend integration
- **State Management**: React Query for server state management
- **Routing**: React Router for client-side navigation
- **Dark Mode**: Built-in theme switching with shadcn/ui design system
- **Responsive Design**: Mobile-first responsive design
- **Accessibility**: WCAG compliant components

## 📁 Project Structure

```
src/
├── components/            # Reusable UI components
│   ├── ui/               # shadcn/ui components (Button, Card, Badge, etc.)
│   └── Layout.tsx        # Main layout wrapper
├── pages/                # Page components with React Router
│   ├── Dashboard.tsx     # Main dashboard
│   ├── Queries.tsx       # Queries management
│   ├── Specifications.tsx # Specifications management
│   ├── Workflows.tsx     # Workflow monitoring
│   └── NotFound.tsx      # 404 page
├── lib/                  # Utility libraries
│   ├── api-client.ts     # HTTP client for FastAPI backend
│   └── utils.ts          # Common utility functions
├── test/                 # Test configuration
│   └── setup.ts          # Test environment setup
├── App.tsx               # Main app component with routing
├── main.tsx              # Vite entry point
└── index.css             # Global styles with Tailwind 4
```

## 🛠 Tech Stack

### Core Framework

- **Vite 7**: Fast build tool and dev server
- **React 18**: UI library with modern hooks
- **TypeScript 5**: Static type checking
- **React Router 6**: Client-side routing

### Styling & UI

- **Tailwind CSS 4**: Utility-first CSS framework with new engine
- **shadcn/ui**: Modern component library built on Radix UI
- **Radix UI**: Accessible component primitives
- **Lucide React**: Icon library
- **Class Variance Authority**: Component variant management
- **Tailwind Merge**: Intelligent Tailwind class merging

### Development Tools

- **Vitest**: Fast unit testing framework
- **ESLint 9**: Code linting with flat config
- **Prettier**: Code formatting
- **TypeScript ESLint**: TypeScript-aware linting

### API & State Management

- **Axios**: HTTP client for API requests
- **React Query**: Server state management and caching
- **React Hook Form**: Form state management
- **Zod**: Runtime type validation

### Testing

- **Vitest**: Test runner with coverage
- **Testing Library**: React component testing
- **jsdom**: DOM testing environment

## 🚦 Getting Started

### Prerequisites

- **Node.js 20+** and npm 10+ (see `.nvmrc`)
- The Julee Example FastAPI backend running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server (Vite)
npm run dev

# Visit http://localhost:3000
```

### Development Scripts

```bash
# Development
npm run dev              # Start Vite dev server
npm run build           # Build for production
npm run preview         # Preview production build
npm start               # Alias for dev

# Testing
npm run test            # Run unit tests
npm run test:ui         # Run tests with Vitest UI
npm run test:coverage   # Run tests with coverage report

# Code Quality
npm run lint            # Run ESLint
npm run format:check    # Check code formatting with Prettier
npm run format:fix      # Fix code formatting
npm run lint-staged     # Run linting on staged files
```

## 🔧 Configuration

### Environment Variables

Copy the example environment file and customize it for your setup:

```bash
# Copy the example file
cp .env.example .env.local

# Edit the file with your specific configuration
# The defaults should work for local development
```

The application uses a centralized configuration system (`src/lib/config.ts`) that validates and processes these environment variables at startup. See `.env.example` for all available configuration options.

### API Integration

The UI connects to your FastAPI backend endpoints:

- **Health Check**: `GET /health`
- **Knowledge Service Queries**: `GET|POST /knowledge_service_queries`
- **Assembly Specifications**: `GET|POST /assembly_specifications`

### Docker Integration

The UI can run alongside the backend using Docker Compose:

```bash
# Start FastAPI backend and dependencies
docker-compose --profile julee up --build

# In another terminal, start the UI
npm run dev
```

## 📚 Component Development

### shadcn/ui Components

The project uses shadcn/ui for consistent, accessible components:

```bash
# Add new shadcn/ui components
npx shadcn@latest add dialog table input textarea

# Components are added to src/components/ui/
```

## 🧪 Testing Strategy

### Unit Testing

Components and utilities will be tested using Vitest:

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test:ui

# Generate coverage report
npm run test:coverage
```

### Test Structure

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Dashboard from '@/pages/Dashboard';

describe('Dashboard', () => {
  it('renders dashboard title', () => {
    render(<Dashboard />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });
});
```

## 📊 Dashboard Features

The main dashboard provides:

- **System Health Monitoring**: Real-time status of API, Temporal, and storage services
- **Workflow Statistics**: Active queries, specifications, and workflows
- **Quick Actions**: Common workflow operations
- **Real-time Updates**: Auto-refreshing data with React Query
- **Responsive Design**: Works on desktop, tablet, and mobile

## 🚀 Production Build

### Build Process

```bash
# Create production build
npm run build

# Preview the build locally
npm run preview

# Build output goes to ./build directory
```

### Deployment

The app builds to static files that can be deployed to:

- **Vercel**: `vercel --prod`
- **Netlify**: Deploy `./build` directory
- **Static Hosting**: Serve `./build` directory
- **Docker**: Can be containerized with nginx

## 🤝 Development Guidelines

### Code Style

- Use **TypeScript** for all new files
- Follow **ESLint** and **Prettier** configurations
- Use **semantic commit messages**
- Write **unit tests** for new components
- Document component APIs with TypeScript interfaces

### Component Guidelines

- Build **accessible components** (ARIA attributes, keyboard navigation)
- Use **shadcn/ui** components as building blocks
- Follow **composition over inheritance**
- Support both **light and dark themes**
- Use **semantic CSS classes** from the design system

### API Integration

- Use **React Query** for server state management
- Implement **proper error handling** with try/catch
- Add **loading states** with skeleton components
- **Type all API responses** with TypeScript interfaces
- Use **environment variables** for API configuration
