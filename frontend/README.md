# Secure-ity Frontend

Modern React + TypeScript frontend with shadcn/ui components for the Secure-ity configuration management system.

## Features

- ⚡ **React 18** with TypeScript
- 🎨 **shadcn/ui** components for beautiful, accessible UI
- 🎯 **Tailwind CSS** for styling
- 🔒 **JWT Authentication** with token refresh
- 📱 **Responsive Design**
- 🚀 **Vite** for fast development and building

## Setup

### Install Dependencies

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000` with Vite's proxy to the Flask backend.

### Build for Production

```bash
npm run build
```

The build output will be in the `dist/` directory, which Flask will serve.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
VITE_API_URL=http://localhost:5000  # Optional, defaults to same origin
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/          # shadcn/ui components
│   │   ├── auth/        # Login, Register
│   │   ├── dashboard/   # Config management
│   │   └── layout/      # Layout components
│   ├── lib/
│   │   ├── api.ts       # API client
│   │   └── utils.ts     # Utilities
│   ├── App.tsx          # Main app component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Components

### Authentication
- `Login.tsx` - User login form
- `Register.tsx` - User registration form

### Dashboard
- `Dashboard.tsx` - Main configuration list view
- `ConfigForm.tsx` - Create new configuration
- `ConfigView.tsx` - View configuration details

### UI Components (shadcn/ui)
- Button, Card, Input, Label, Textarea
- Toast notifications
- Alert Dialog

## API Integration

The frontend uses the API client in `src/lib/api.ts` which:
- Handles JWT token management
- Automatically refreshes tokens on expiration
- Provides type-safe API methods
- Manages authentication state

## Styling

Uses Tailwind CSS with shadcn/ui theme. Colors and styling can be customized in:
- `tailwind.config.js` - Tailwind configuration
- `src/index.css` - CSS variables for theming

## Building for Production

The build process:
1. TypeScript compilation
2. React bundling with Vite
3. Output to `dist/` directory
4. Flask serves the `dist/` directory as static files

## Deployment

The frontend is built as part of the Docker image. The Flask Dockerfile uses a multi-stage build:
1. Build React app
2. Copy build output to Flask container
3. Flask serves the static files

