/**
 * The 8 angular coordinates θ₀…θ₇ of T⁸, indexed by the grade basis of the
 * Clifford algebra Cl(3,0) — equivalently, the subsets of {1,2,3}.
 *
 * The Clifford algebra supplies ONLY this indexing. The noncommutativity comes
 * from the deformation matrix Θ, not from Clifford multiplication.
 *
 * The subset {a,b,c} ⊆ {1,2,3} places each index at a cube corner
 * (x,y,z) ∈ {0,1}³, where x marks "contains 1", y "contains 2", z "contains 3".
 */

export interface Coord {
  index: number;
  /** Rendered Clifford label, e.g. "e_{23}". */
  label: string;
  /** Plain label for tooltips, e.g. "e23". */
  plain: string;
  /** Subset of {1,2,3}. */
  subset: number[];
  /** Clifford grade = |subset|. */
  grade: number;
  /** Cube corner (a,b,c) ∈ {0,1}³ — a=contains1, b=contains2, c=contains3. */
  corner: [number, number, number];
}

export const COORDS: Coord[] = [
  { index: 0, label: '1',        plain: '1',   subset: [],        grade: 0, corner: [0, 0, 0] },
  { index: 1, label: 'e_{1}',    plain: 'e1',  subset: [1],       grade: 1, corner: [1, 0, 0] },
  { index: 2, label: 'e_{2}',    plain: 'e2',  subset: [2],       grade: 1, corner: [0, 1, 0] },
  { index: 3, label: 'e_{3}',    plain: 'e3',  subset: [3],       grade: 1, corner: [0, 0, 1] },
  { index: 4, label: 'e_{23}',   plain: 'e23', subset: [2, 3],    grade: 2, corner: [0, 1, 1] },
  { index: 5, label: 'e_{13}',   plain: 'e13', subset: [1, 3],    grade: 2, corner: [1, 0, 1] },
  { index: 6, label: 'e_{12}',   plain: 'e12', subset: [1, 2],    grade: 2, corner: [1, 1, 0] },
  { index: 7, label: 'I=e_{123}', plain: 'I',  subset: [1, 2, 3], grade: 3, corner: [1, 1, 1] },
];

/** Grade dimensions (1, 3, 3, 1). */
export const GRADE_DIMS = [1, 3, 3, 1];

/** Centered cube position for corner (a,b,c): maps {0,1} -> {-1,+1}. */
export function cornerPosition(c: [number, number, number], size = 1): [number, number, number] {
  return [(c[0] * 2 - 1) * size, (c[1] * 2 - 1) * size, (c[2] * 2 - 1) * size];
}
