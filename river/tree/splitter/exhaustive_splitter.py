from collections import Counter, defaultdict

from .._attribute_test import AttributeSplitSuggestion, NumericAttributeBinaryTest
from .base_splitter import Splitter


class ExhaustiveSplitter(Splitter):
    """Numeric attribute observer for classification tasks that is based on
    a Binary Search Tree.

    This algorithm is also referred to as exhaustive attribute observer,
    since it ends up storing all the observations between split attempts.

    This splitter cannot perform probability density estimations, so it does not work well
    when coupled with tree leaves using naive bayes models.
    """

    class Node:
        def __init__(self, att_val, target_val, sample_weight):
            self.class_count_left = defaultdict(float)
            self.class_count_right = defaultdict(float)
            self._left = None
            self._right = None

            self.cut_point = att_val
            self.class_count_left[target_val] += sample_weight

        def insert_value(self, val, label, sample_weight):
            if val == self.cut_point:
                self.class_count_left[label] += sample_weight
            elif val < self.cut_point:
                self.class_count_left[label] += sample_weight
                if self._left is None:
                    self._left = ExhaustiveSplitter.Node(val, label, sample_weight)
                else:
                    self._left.insert_value(val, label, sample_weight)
            else:
                self.class_count_right[label] += sample_weight
                if self._right is None:
                    self._right = ExhaustiveSplitter.Node(val, label, sample_weight)
                else:
                    self._right.insert_value(val, label, sample_weight)

    def __init__(self):
        super().__init__()
        self._root = None

    def update(self, att_val, target_val, sample_weight):
        if att_val is None:
            return
        else:
            if self._root is None:
                self._root = ExhaustiveSplitter.Node(att_val, target_val, sample_weight)
            else:
                self._root.insert_value(att_val, target_val, sample_weight)

        return self

    def cond_proba(self, att_val, class_val):
        """The underlying data structure used to monitor the input does not allow probability
        density estimations. Hence, it always returns zero for any given input."""
        return 0.0

    def best_evaluated_split_suggestion(
        self, criterion, pre_split_dist, att_idx, binary_only
    ):
        current_best_option = AttributeSplitSuggestion(None, [{}], -float("inf"))

        return self._search_for_best_split_option(
            current_node=self._root,
            current_best_option=current_best_option,
            actual_parent_left=None,
            parent_left=None,
            parent_right=None,
            left_child=False,
            criterion=criterion,
            pre_split_dist=pre_split_dist,
            att_idx=att_idx,
        )

    def _search_for_best_split_option(
        self,
        current_node,
        current_best_option,
        actual_parent_left,
        parent_left,
        parent_right,
        left_child,
        criterion,
        pre_split_dist,
        att_idx,
    ):
        if current_node is None:
            return current_best_option

        left_dist = {}
        right_dist = {}

        if parent_left is None:
            left_dist.update(
                dict(Counter(left_dist) + Counter(current_node.class_count_left))
            )
            right_dist.update(
                dict(Counter(right_dist) + Counter(current_node.class_count_right))
            )
        else:
            left_dist.update(dict(Counter(left_dist) + Counter(parent_left)))
            right_dist.update(dict(Counter(right_dist) + Counter(parent_right)))

            if left_child:
                # get the exact statistics of the parent value
                exact_parent_dist = {}
                exact_parent_dist.update(
                    dict(Counter(exact_parent_dist) + Counter(actual_parent_left))
                )
                exact_parent_dist.update(
                    dict(
                        Counter(exact_parent_dist)
                        - Counter(current_node.class_count_left)
                    )
                )
                exact_parent_dist.update(
                    dict(
                        Counter(exact_parent_dist)
                        - Counter(current_node.class_count_right)
                    )
                )

                # move the subtrees
                left_dist.update(
                    dict(Counter(left_dist) - Counter(current_node.class_count_right))
                )
                right_dist.update(
                    dict(Counter(right_dist) + Counter(current_node.class_count_right))
                )

                # move the exact value from the parent
                right_dist.update(
                    dict(Counter(right_dist) + Counter(exact_parent_dist))
                )
                left_dist.update(dict(Counter(left_dist) - Counter(exact_parent_dist)))
            else:
                left_dist.update(
                    dict(Counter(left_dist) + Counter(current_node.class_count_left))
                )
                right_dist.update(
                    dict(Counter(right_dist) - Counter(current_node.class_count_left))
                )

        post_split_dists = [left_dist, right_dist]
        merit = criterion.merit_of_split(pre_split_dist, post_split_dists)

        if current_best_option is None or merit > current_best_option.merit:
            num_att_binary_test = NumericAttributeBinaryTest(
                att_idx=att_idx,
                att_value=current_node.cut_point,
                equal_passes_test=True,
            )
            current_best_option = AttributeSplitSuggestion(
                split_test=num_att_binary_test,
                resulting_class_distributions=post_split_dists,
                merit=merit,
            )

        current_best_option = self._search_for_best_split_option(
            current_node=current_node._left,  # noqa
            current_best_option=current_best_option,
            actual_parent_left=current_node.class_count_left,
            parent_left=post_split_dists[0],
            parent_right=post_split_dists[1],
            left_child=True,
            criterion=criterion,
            pre_split_dist=pre_split_dist,
            att_idx=att_idx,
        )

        current_best_option = self._search_for_best_split_option(
            current_node=current_node._right,  # noqa
            current_best_option=current_best_option,
            actual_parent_left=current_node.class_count_left,
            parent_left=post_split_dists[0],
            parent_right=post_split_dists[1],
            left_child=False,
            criterion=criterion,
            pre_split_dist=pre_split_dist,
            att_idx=att_idx,
        )

        return current_best_option
