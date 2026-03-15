import { useState, useEffect } from 'react';
import { getBookStoreVersion, onBookStoreChange } from './book-store';

/** React hook that re-renders when book store changes (including background updates). */
export function useBookStoreVersion(): number {
  const [version, setVersion] = useState(getBookStoreVersion);
  useEffect(() => onBookStoreChange(() => setVersion(getBookStoreVersion())), []);
  return version;
}
