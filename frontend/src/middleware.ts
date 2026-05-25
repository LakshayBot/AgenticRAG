import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Auth is handled client-side via the AuthGuard component.
// This middleware just ensures public paths are accessible.
export function middleware(request: NextRequest) {
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)', '/'],
}
