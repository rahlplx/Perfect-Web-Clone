'use client';

import Image from 'next/image';
import Link from 'next/link';
import { Brand } from '@/types/landing';

export function BrandLogo({ brand }: { brand: Brand }) {
  const isSvg = brand.logo?.src.endsWith('.svg');

  return (
    <Link
      href={brand.url || '/'}
      target={brand.target || '_self'}
      className={`flex items-center space-x-3 ${brand.className || ''}`}
    >
      {brand.logo && (
        <Image
          src={brand.logo.src}
          alt={brand.title ? '' : brand.logo.alt || ''}
          width={brand.logo.width || 80}
          height={brand.logo.height || 80}
          className={isSvg ? "h-10 w-auto" : "h-8 w-auto rounded-lg"}
          unoptimized={brand.logo.src.startsWith('http') || isSvg}
        />
      )}
      {brand.title && (
        <span className="text-lg font-medium">{brand.title}</span>
      )}
    </Link>
  );
}
