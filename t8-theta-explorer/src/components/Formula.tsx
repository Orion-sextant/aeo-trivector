import { useMemo } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';

/** Inline or block KaTeX. Falls back to raw text if KaTeX throws. */
export function Formula({ tex, block = false }: { tex: string; block?: boolean }) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(tex, { displayMode: block, throwOnError: false });
    } catch {
      return tex;
    }
  }, [tex, block]);
  return (
    <span
      className={block ? 'katex-block' : 'katex-inline'}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
