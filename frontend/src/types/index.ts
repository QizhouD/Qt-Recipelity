// Frontend type definitions matching the OpenAPI contract

export interface Ingredient {
  id: number;
  name: string;
  amount?: number;
  unit?: string;
}

export interface Step {
  id: number;
  order: number;
  description: string;
}

export interface Nutrition {
  id: number;
  calories?: number;
  protein?: number;
  fat?: number;
  carbohydrates?: number;
  fiber?: number;
  sugar?: number;
  sodium?: number;
  source?: string;
  calculated_at?: string;
  matched_ingredients?: number;
  unmatched_ingredients?: string[];
}

export interface Tag {
  id: number;
  name: string;
}

export interface RecipeSummary {
  id: number;
  name: string;
  prep_time?: number;
  cook_time?: number;
  difficulty?: number;
  cuisine?: string;
  image_url?: string;
  tags: Tag[];
  created_at?: string;
}

export interface RecipeDetail extends RecipeSummary {
  description?: string;
  total_time: number;
  source_url?: string;
  updated_at?: string;
  ingredients: Ingredient[];
  steps: Step[];
  nutrition?: Nutrition;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
}

export interface RecipeSearchFilters {
  keyword: string;
  cuisine: string;
  tags: string[];
  min_time?: number;
  max_time?: number;
  min_difficulty?: number;
  max_difficulty?: number;
}

export interface AIRecipeDraft {
  name: string;
  description?: string;
  prep_time?: number;
  cook_time?: number;
  difficulty?: number;
  cuisine?: string;
  image_url?: string;
  ingredients: { name: string; amount?: number; unit?: string }[];
  steps: { order: number; description: string }[];
  nutrition?: Omit<Nutrition, "id">;
  tags: string[];
  confidence: number;
  warnings: string[];
  provider: string;
}

export interface GeneratedImage {
  image_url: string;
  provider: string;
  revised_prompt?: string;
}
