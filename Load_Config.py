

class Config:
    def __init__(self, fname="default.conf", directory="."):
        self.fname = fname
        self.main_dict = {}
        self.subdicts = []

        config = open(directory + "/" + fname, "r")
        line = config.readline()

        current_dict = None

        while line != '':
            line = line.replace("\n", "")
            if "#" in line:
                line = line[:line.index("#")]
            if len(line) > 0 and line[0] == "[":
                current_dict = line[1:line.index("]")]
                self.subdicts.append(current_dict)
                self.main_dict[current_dict] = {}
            if "=" in line:
                splited = line.replace("=", "").split(" ")
                if current_dict is None:
                    self.main_dict[splited[0]] = splited[-1]
                else:
                    self.main_dict[current_dict][splited[0]] = splited[-1]

            line = config.readline()
        config.close()

        print(self.main_dict)

        
if __name__ == '__main__':
    main_class = Config("Test.conf")
