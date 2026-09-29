def calculate_grade(marks):
    if marks >= 90:
        return 'A'
    elif marks >= 80:
        return 'B'
    elif marks >= 70:
        return 'C'
    elif marks >= 60:
        return 'D'
    else:
        return 'E'

if __name__ == "__main__":
    
        while True:
            try:
                mark = int(input(f"Enter mark (0-100): "))
                if 0 <= mark <= 100:
                    grade = calculate_grade(mark)
                    print(f"Mark: {mark}, Grade: {grade}")
                else:
                    print("Invalid mark. Please enter a number between 0 and 100.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")
            except Exception as e:
                print(f"An error occurred: {e}")
            except KeyboardInterrupt:
                raise SystemExit
    