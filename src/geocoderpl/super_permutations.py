""" Class that calculates indices providing superpermutations for lists of strings with length of maximum 5 elements """

from itertools import permutations as perms


class SuperPerms(object):
    def __init__(self, max_v: int) -> None:
        self.max_v = max_v
        self.all_inds = list(range(self.max_v))
        self.base_vals = "".join([str(i) for i in self.all_inds])
        self.all_perms = [[prm for prm in perms(self.base_vals, i)] for i in self.all_inds[1:]]
        self.c_perms = ["".join(prm) for prm in perms(self.base_vals, self.max_v) if "".join(prm) != self.base_vals]
        self.fin_super_perm_ids = self.get_super_perm()

    def get_super_perm(self, p_vals: str = None, c_perms: list = None) -> list:
        """ Function that finds final superpermutation (shortests list of indices) """

        if p_vals is None:
            p_vals, c_perms = str(self.base_vals), self.c_perms

        for c_perm in self.all_perms:
            for val in c_perm:
                c_val = "".join([str(v) for v in val])
                n_val = p_vals + c_val

                if c_val != p_vals[-1] and n_val[-self.max_v:] in c_perms:
                    c_perms.remove(n_val[-self.max_v:])
                    return [int(s) for s in n_val[:-(self.max_v - 1)].strip("")] + self.get_super_perm(n_val[-(
                            self.max_v - 1):], c_perms) if c_perms else [int(s) for s in n_val.strip("")]
        return [0]
