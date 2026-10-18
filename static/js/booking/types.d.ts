export type InputType = 'single_select' | 'multi_select' | 'boolean' | 'text' | 'textarea' | 'number' | 'photo' | 'file';
export type OptionSelection = string | string[] | boolean | number | {name: string} | null;
export interface BookingSelection {
  clientTypeId: string | null;
  categoryId: string | null;
  subcategoryId: string | null;
  selectedOptions: Record<string, OptionSelection>;
  calculatedPrice: number;
  calculatedDurationMinutes: number;
}
export interface OptionValue {
  id: string; label: string; value: string; description: string; imageUrl: string;
  priceAdjustment: string; durationAdjustmentMinutes: number;
  metadata?: {color?: string};
}
export interface OptionGroup {
  id: string; name: string; description: string; inputType: InputType;
  required: boolean; values: OptionValue[]; metadata?: {presentation?: 'color'};
}
export interface Subcategory {
  id: string; name: string; description: string; imageUrl: string;
  priceAdjustment: string; durationAdjustmentMinutes: number; groups: OptionGroup[];
}
export interface Category {
  id: string; name: string; description: string; imageUrl: string;
  basePrice: string; baseDurationMinutes: number;
  priceType: 'fixed' | 'starting_at' | 'consultation_required';
  clientTypeIds: string[]; groups: OptionGroup[]; subcategories: Subcategory[];
}
export interface Catalogue {
  clientTypes: {id: string; name: string; description: string}[];
  categories: Category[];
}
