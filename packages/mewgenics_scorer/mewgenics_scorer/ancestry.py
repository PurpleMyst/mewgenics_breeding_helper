from mewgenics_parser.cat import Cat


class KinshipManager:
    """
    Computes and stores the additive kinship matrix for a fixed population of cats.
    Expects a complete dataset and handles topological sorting internally.
    """

    def __init__(self, cats: list[Cat]):
        self._processed_cats: list[Cat] = []
        self._kinship_matrix: dict[int, list[float]] = {}

        # Internally resolve the DAG to ensure parents are processed before children
        sorted_cats = self._topological_sort(cats)
        self._initialize_matrix(sorted_cats)

    def _topological_sort(self, cats: list[Cat]) -> list[Cat]:
        """
        Sorts cats such that all parents appear before their children.
        Includes cycle detection to prevent infinite recursion on corrupted save data.
        """
        visited = set()
        visiting = set()
        topo_order = []

        # Map for quick lookup of cats that are actually in the provided dataset
        cat_map = {cat.db_key: cat for cat in cats}

        def dfs(cat: Cat) -> None:
            if cat.db_key in visited:
                return
            if cat.db_key in visiting:
                raise ValueError(
                    f"Pedigree cycle detected involving cat {cat.db_key}. Save data may be corrupted."
                )

            visiting.add(cat.db_key)

            # Recurse up the DAG if the parent exists in our dataset
            if cat.parent_a and cat.parent_a.db_key in cat_map:
                dfs(cat_map[cat.parent_a.db_key])
            if cat.parent_b and cat.parent_b.db_key in cat_map:
                dfs(cat_map[cat.parent_b.db_key])

            visiting.remove(cat.db_key)
            visited.add(cat.db_key)
            topo_order.append(cat)

        for cat in cats:
            dfs(cat)

        return topo_order

    def _get_index(self, cat: Cat | None) -> int:
        """Helper to find the internal matrix index of a cat."""
        if cat is None:
            return -1
        try:
            return self._processed_cats.index(cat)
        except ValueError:
            return -1

    def _initialize_matrix(self, sorted_cats: list[Cat]) -> None:
        """
        Builds the additive kinship matrix from the topologically sorted list.
        """
        for cat in sorted_cats:
            idx_mom = self._get_index(cat.parent_a)
            idx_dad = self._get_index(cat.parent_b)

            # 1. Determine base inbreeding (f) from parents' kinship
            f = 0.0
            if idx_mom != -1 and idx_dad != -1 and cat.parent_a is not None:
                f = self._kinship_matrix[cat.parent_a.db_key][idx_dad]

            new_vector: list[float] = []

            # 2. Calculate cross-kinship with all previously processed cats
            for existing_cat in self._processed_cats:
                k_mom = (
                    self._kinship_matrix[existing_cat.db_key][idx_mom]
                    if idx_mom != -1
                    else 0.0
                )
                k_dad = (
                    self._kinship_matrix[existing_cat.db_key][idx_dad]
                    if idx_dad != -1
                    else 0.0
                )

                psi_x_y = 0.5 * (k_mom + k_dad)

                # Update the older cat's vector and the new cat's vector
                self._kinship_matrix[existing_cat.db_key].append(psi_x_y)
                new_vector.append(psi_x_y)

            # 3. Calculate self-kinship
            psi_y_y = 0.5 * (1.0 + f)
            new_vector.append(psi_y_y)

            # 4. Commit to state
            self._kinship_matrix[cat.db_key] = new_vector
            self._processed_cats.append(cat)

    def get_inbreeding_coefficient(self, cat: Cat) -> float:
        """
        Retrieves the exact inbreeding coefficient (f) for a cat in the dataset.
        """
        idx = self._get_index(cat)
        if idx == -1:
            return 0.0

        self_kinship = self._kinship_matrix[cat.db_key][idx]
        return (2.0 * self_kinship) - 1.0

    def calculate_hypothetical_inbreeding(self, parent_a: Cat, parent_b: Cat) -> float:
        """
        Calculates the predicted inbreeding coefficient for an offspring of two cats.
        """
        idx_a = self._get_index(parent_a)
        idx_b = self._get_index(parent_b)

        if idx_a == -1 or idx_b == -1:
            return 0.0

        return self._kinship_matrix[parent_a.db_key][idx_b]
