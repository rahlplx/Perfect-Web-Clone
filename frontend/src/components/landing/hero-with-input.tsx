'use client';

import { useState, useEffect } from 'react';
import { ArrowRight, Globe, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

import { SmartIcon } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Highlighter } from '@/components/ui/highlighter';
import { cn } from '@/lib/utils';
import { Section } from '@/types/landing';

function formatStars(count: number): string {
  return count.toLocaleString();
}

export function HeroWithInput({
  section,
  className,
}: {
  section: Section;
  className?: string;
}) {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [githubStars, setGithubStars] = useState<number | null>(null);

  // Fetch GitHub stars
  useEffect(() => {
    const fetchStars = async () => {
      try {
        const response = await fetch('https://api.github.com/users/ericshang98/repos?per_page=100');
        if (response.ok) {
          const repos = await response.json();
          const totalStars = repos.reduce((sum: number, r: { stargazers_count: number }) => sum + r.stargazers_count, 0);
          setGithubStars(totalStars);
        }
      } catch (error) {
        console.error('Failed to fetch GitHub stars:', error);
      }
    };
    fetchStars();
  }, []);

  const highlightText = section.highlight_text ?? '';
  let texts = null;
  if (highlightText) {
    texts = section.title?.split(highlightText, 2);
  }

  const isValidUrl = (string: string) => {
    try {
      const url = new URL(string.startsWith('http') ? string : `https://${string}`);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }

    const fullUrl = url.startsWith('http') ? url : `https://${url}`;

    if (!isValidUrl(fullUrl)) {
      setError('Please enter a valid URL');
      return;
    }

    setIsLoading(true);

    // Navigate to extractor with the URL
    router.push(`/extractor?url=${encodeURIComponent(fullUrl)}`);
  };

  return (
    <section
      id={section.id}
      className={cn(
        `pt-24 pb-8 md:pt-36 md:pb-8`,
        section.className,
        className
      )}
    >
      {section.announcement && (
        <Link
          href={section.announcement.url || ''}
          target={section.announcement.target || '_self'}
          className="hover:bg-background dark:hover:border-t-border bg-muted group mx-auto mb-8 flex w-fit items-center gap-4 rounded-full border p-1 pl-4 shadow-md shadow-zinc-950/5 transition-colors duration-300 dark:border-t-white/5 dark:shadow-zinc-950"
        >
          <span className="text-foreground text-sm">
            {section.announcement.title}
          </span>
          <span className="dark:border-background block h-4 w-0.5 border-l bg-white dark:bg-zinc-700"></span>

          <div className="bg-background group-hover:bg-muted size-6 overflow-hidden rounded-full duration-500">
            <div className="flex w-12 -translate-x-1/2 duration-500 ease-in-out group-hover:translate-x-0">
              <span className="flex size-6">
                <ArrowRight className="m-auto size-3" />
              </span>
              <span className="flex size-6">
                <ArrowRight className="m-auto size-3" />
              </span>
            </div>
          </div>
        </Link>
      )}

      <div className="relative mx-auto max-w-full px-4 text-center md:max-w-5xl">
        {texts && texts.length > 0 ? (
          <h1 className="text-foreground text-4xl font-semibold text-balance sm:mt-12 sm:text-6xl">
            {texts[0]}
            <Highlighter action="underline" color="#EF4444">
              {highlightText}
            </Highlighter>
            {texts[1]}
          </h1>
        ) : (
          <h1 className="text-foreground text-4xl font-semibold text-balance sm:mt-12 sm:text-6xl">
            {section.title}
          </h1>
        )}

        <p
          className="text-muted-foreground mt-8 mb-8 text-lg text-balance"
          dangerouslySetInnerHTML={{ __html: section.description ?? '' }}
        />

        {/* URL Input Form */}
        <form onSubmit={handleSubmit} className="mx-auto max-w-2xl mb-8">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Globe className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Enter any website URL to clone..."
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setError('');
                }}
                className="h-14 pl-12 pr-4 text-lg rounded-xl border-2 focus:border-primary"
              />
            </div>
            <Button
              type="submit"
              size="lg"
              disabled={isLoading}
              className="h-14 px-8 text-lg rounded-xl"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Extracting...
                </>
              ) : (
                <>
                  <SmartIcon name="Zap" className="mr-2 h-5 w-5" />
                  Clone Now
                </>
              )}
            </Button>
          </div>
          {error && (
            <p className="text-destructive text-sm mt-2 text-left">{error}</p>
          )}
          <p className="text-muted-foreground text-sm mt-3">
            Try: stripe.com, vercel.com, linear.app, or any website
          </p>
        </form>

        {/* GitHub Support Banner */}
        <Link
          href="https://github.com/ericshang98"
          target="_blank"
          className="mx-auto mb-8 flex w-fit items-center gap-3 rounded-full bg-muted/50 border border-border/50 px-5 py-2.5 transition-all hover:bg-muted hover:border-border"
        >
          <SmartIcon name="Github" className="h-5 w-5" />
          <span className="text-sm font-medium">GitHub</span>
          {githubStars !== null && (
            <span className="text-sm text-muted-foreground">
              {formatStars(githubStars)} stars
            </span>
          )}
        </Link>

        {section.buttons && section.buttons.length > 0 && (
          <div className="flex items-center justify-center gap-4 mb-8">
            {section.buttons.map((button, idx) => (
              <Button
                asChild
                size={button.size || 'default'}
                variant={button.variant || 'outline'}
                className="px-4 text-sm"
                key={idx}
              >
                <Link href={button.url ?? ''} target={button.target ?? '_self'}>
                  {button.icon && <SmartIcon name={button.icon as string} />}
                  <span>{button.title}</span>
                </Link>
              </Button>
            ))}
          </div>
        )}

        {section.tip && (
          <p
            className="text-muted-foreground mt-6 block text-center text-sm"
            dangerouslySetInnerHTML={{ __html: section.tip ?? '' }}
          />
        )}
      </div>
    </section>
  );
}
