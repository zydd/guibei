
type mat: (pair, pair)

impl mat:
    func print(self: Self):
        bytes.print("[")
        self.0.print()
        bytes.print(", ")
        self.1.print()
        bytes.print("]")

func main():
    mat(pair(1, 2), pair(3, 4)).print()
    bytes.print("\n")
