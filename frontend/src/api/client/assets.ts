/** Uploaded image retrieval preserves the existing unauthenticated fetch behavior. */
export async function fetchEvidenceBlob(url: string): Promise<Blob | undefined> {
  const response = await fetch(url)
  return response.ok ? response.blob() : undefined
}
