import type { FeelingsAnswers } from '../types'

export function defaultFeelings(): FeelingsAnswers {
  return {
    joy: { value: 3, na: false },
    serenity: { value: 3, na: false },
    anger: { value: 3, na: false },
    fear: { value: 3, na: false },
  }
}
