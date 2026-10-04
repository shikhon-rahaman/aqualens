/** Margin field helpers: image L/R → stream L/R only when facing downstream. */

export const MARGIN_FIELD_IDS = [
  'impervious_left',
  'impervious_right',
  'vegetation_left',
  'vegetation_right',
  'veg_type_left',
  'veg_type_right',
] as const

export type MarginFieldId = (typeof MARGIN_FIELD_IDS)[number]

export function isMarginField(fieldId: string): boolean {
  return (MARGIN_FIELD_IDS as readonly string[]).includes(fieldId)
}

/**
 * AI returns image-left/right. Apply those suggestions to stream left/right
 * fields only when the citizen confirmed they faced downstream.
 */
export function shouldApplyAiMarginSuggestion(
  fieldId: string,
  facingDownstream: boolean,
): boolean {
  if (!isMarginField(fieldId)) return true
  return facingDownstream
}

export const GROUP_TITLES: Record<string, string> = {
  questions_1: 'Channel, bed and flow',
  questions_2: 'Water look and pressures',
  questions_3: 'Margins and banks',
  feedback: 'Your rating and feelings',
}

export const SOURCE_LABELS: Record<string, string> = {
  ai_accepted: 'AI accepted',
  ai_edited: 'AI edited',
  human: 'Entered by you',
  unanswered: 'Not answered',
}
