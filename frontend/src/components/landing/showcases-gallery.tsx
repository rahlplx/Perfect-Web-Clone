"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, X, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ShowcaseItem {
  title: string;
  description?: string;
  url?: string;
  target?: string;
  image?: {
    src: string;
    alt: string;
  };
  source_url?: string;
}

interface ShowcasesGalleryProps {
  id?: string;
  label?: string;
  title: string;
  description: string;
  items: ShowcaseItem[];
  buttons?: Array<{
    title: string;
    url: string;
    variant?: "default" | "outline";
    target?: string;
  }>;
  className?: string;
}

export function ShowcasesGallery({
  id,
  label,
  title,
  description,
  items,
  buttons,
  className,
}: ShowcasesGalleryProps) {
  const [selectedItem, setSelectedItem] = useState<ShowcaseItem | null>(null);

  return (
    <section id={id} className={cn("py-16 md:py-24", className)}>
      <div className="container">
        <motion.div
          className="mb-10 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          {label && (
            <span className="text-primary mb-2 block text-sm font-medium uppercase tracking-wider">
              {label}
            </span>
          )}
          <h2 className="text-foreground mb-4 text-3xl font-bold lg:text-4xl">
            {title}
          </h2>
          <p className="text-muted-foreground mx-auto max-w-2xl text-lg">
            {description}
          </p>
        </motion.div>

        {/* Grid Layout - 3 per row */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3">
          {items.map((item, index) => (
            <motion.div
              key={index}
              className="group relative cursor-pointer overflow-hidden rounded-lg border bg-card shadow-sm transition-all hover:shadow-md hover:border-primary/50"
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-20px" }}
              transition={{
                duration: 0.4,
                delay: index * 0.03,
              }}
              onClick={() => setSelectedItem(item)}
            >
              {/* Two images side by side */}
              <div className="flex gap-2 p-3">
                {/* Website Screenshot */}
                <div className="relative aspect-[4/3] flex-1 overflow-hidden rounded-md bg-muted">
                  {item.image?.src ? (
                    <Image
                      src={item.image.src}
                      alt={item.image.alt || item.title}
                      fill
                      sizes="(max-width: 640px) 50vw, (max-width: 768px) 25vw, 16vw"
                      className="object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <span className="text-muted-foreground text-2xl font-bold opacity-20">
                        Web
                      </span>
                    </div>
                  )}
                  {/* Label */}
                  <div className="absolute bottom-1 left-1 rounded bg-black/60 px-1.5 py-0.5 text-[10px] text-white">
                    Website
                  </div>
                </div>

                {/* Dialog/Chat Thumbnail */}
                <div className="relative aspect-[4/3] flex-1 overflow-hidden rounded-md bg-muted">
                  <div className="flex h-full items-center justify-center">
                    <span className="text-muted-foreground text-2xl font-bold opacity-20">
                      Chat
                    </span>
                  </div>
                  {/* Label */}
                  <div className="absolute bottom-1 left-1 rounded bg-black/60 px-1.5 py-0.5 text-[10px] text-white">
                    Dialog
                  </div>
                </div>
              </div>

              {/* Hover Overlay */}
              <div className="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 transition-opacity group-hover:opacity-100 rounded-lg">
                <Eye className="h-6 w-6 text-white" />
              </div>

              <div className="px-3 pb-3">
                <h3 className="truncate text-sm font-medium text-foreground">
                  {item.title}
                </h3>
                {item.description && (
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {item.description}
                  </p>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Empty State */}
        {items.length === 0 && (
          <motion.div
            className="py-16 text-center"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            <p className="text-muted-foreground mb-4 text-lg">
              No cloned pages yet
            </p>
            <Button asChild>
              <Link href="/extractor">Clone Your First Page</Link>
            </Button>
          </motion.div>
        )}

        {/* View All Button */}
        {items.length > 0 && buttons && buttons.length > 0 && (
          <motion.div
            className="mt-8 text-center"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            {buttons.map((button, idx) => (
              <Button
                key={idx}
                asChild
                variant={button.variant || "outline"}
                size="lg"
              >
                <Link href={button.url} target={button.target || "_self"}>
                  {button.title}
                </Link>
              </Button>
            ))}
          </motion.div>
        )}
      </div>

      {/* Modal for Selected Item */}
      <AnimatePresence>
        {selectedItem && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedItem(null)}
          >
            <motion.div
              className="relative max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-xl bg-background shadow-2xl"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close Button */}
              <button
                onClick={() => setSelectedItem(null)}
                className="absolute right-4 top-4 z-10 rounded-full bg-background/80 p-2 transition-colors hover:bg-background"
              >
                <X className="h-5 w-5" />
              </button>

              {/* Image */}
              <div className="relative aspect-video w-full bg-muted">
                {selectedItem.image?.src ? (
                  <Image
                    src={selectedItem.image.src}
                    alt={selectedItem.image.alt || selectedItem.title}
                    fill
                    className="object-contain"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <span className="text-muted-foreground text-6xl font-bold opacity-20">
                      {selectedItem.title.charAt(0).toUpperCase()}
                    </span>
                  </div>
                )}
              </div>

              {/* Details */}
              <div className="p-6">
                <h3 className="mb-2 text-xl font-semibold">{selectedItem.title}</h3>
                {selectedItem.description && (
                  <p className="text-muted-foreground mb-4">
                    {selectedItem.description}
                  </p>
                )}
                <div className="flex gap-3">
                  {selectedItem.url && (
                    <Button asChild>
                      <Link
                        href={selectedItem.url}
                        target={selectedItem.target || "_blank"}
                      >
                        <ExternalLink className="mr-2 h-4 w-4" />
                        View Clone
                      </Link>
                    </Button>
                  )}
                  {selectedItem.source_url && (
                    <Button variant="outline" asChild>
                      <a
                        href={selectedItem.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="mr-2 h-4 w-4" />
                        Original Site
                      </a>
                    </Button>
                  )}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
