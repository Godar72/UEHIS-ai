import React from 'react';
import Image from 'next/image';
import Link from 'next/link';

interface BrandLogoProps {
  variant?: 'light' | 'dark';
  width?: number;
  height?: number;
  className?: string;
  withLink?: boolean;
}

export function BrandLogo({
  variant = 'light',
  width = 120,
  height = 40,
  className = '',
  withLink = true,
}: BrandLogoProps) {
  const logo = (
    <div className={`brand-logo ${className}`} style={{ position: 'relative', width, height }}>
      <Image
        src="/logo.png"
        alt="UEHIS Logo"
        fill
        sizes="120px"
        style={{ objectFit: 'contain', objectPosition: 'left' }}
        priority
      />
    </div>
  );

  if (withLink) {
    return (
      <Link href="/" aria-label="UEHIS Homepage">
        {logo}
      </Link>
    );
  }

  return logo;
}
