func main() -> ():
    match char "5":
        case "0": bytes.print("zero\n")
        case "1": bytes.print("one\n")
        case "2": bytes.print("two\n")
        case "3": bytes.print("three\n")
        case "4": bytes.print("four\n")
        case "5": bytes.print("five\n")

    match Option Option.Some(3):
        case Option.None:
            assert(False)
        case Option.Some(value):
            assert(True)
