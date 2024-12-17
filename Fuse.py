#!/usr/bin/env python3
"""
    This is a simple threshold fuse class. If value become greater that the threshold, flag is set to True.
    If the value is below/falls below the threshold value, flag is set to False. It has minimum and maximum values.
    This is done so that actual value would not drift too much into any direction. To increase the value, run reward()
    function. To decrease the value, run punish() function. Increment(reward), decrement(punishment), threshold,
    minimum and maximum values can be set in the constructor. __bool__() function allow checking flag status inside if
    statements without calling any functions, so code like this is valid:
        some_threshold = Fuse()
        // punish and/or reward one or more times
        if some_threshold:
            print("Threshold reached!")
        else:
            print("Threshold is not reached")
    Example use code provided at the bottom of the file under "if __name__ == '__main__':".
"""


class Fuse:
    def __init__(self, config_dict: dict):
        """

        :type config_dict: dict
        """
        if 'threshold' in config_dict:
            self.t_hold = int(config_dict['threshold'])
        else:
            self.t_hold = 5

        if 'reward' in config_dict:
            self.reward_val = int(config_dict['reward'])
        else:
            self.reward_val = 1

        if 'fine' in config_dict:
            self.fine = float(config_dict['fine'])
        else:
            self.fine = 0.2

        if 'minimum' in config_dict:
            self.minimum = int(config_dict['minimum'])
        else:
            self.minimum = 0

        if 'maximum' in config_dict:
            self.maximum = int(config_dict['maximum'])
        else:
            self.maximum = 6
        self.value = float(self.minimum)
        self.flag = False

    def punish(self):
        self.value -= self.fine
        if self.value < self.minimum:
            self.value = self.minimum
            self.flag = False
        elif self.value < self.t_hold:
            self.flag = False

    def reward(self):
        self.value += self.reward_val
        if self.value > self.maximum:
            self.value = self.maximum
            self.flag = True
        elif self.value >= self.t_hold:
            self.flag = True

    def __bool__(self):
        return self.flag

    def __float__(self):
        return self.value

    def __str__(self):
        return (f'Flag: {self.flag}\n'
                f'Value: {self.value}\n'
                f'Threshold: {self.t_hold}\n'
                f'Reward: {self.reward_val}\n'
                f'Punishment: {self.fine}\n'
                f'Maximum: {self.maximum}\n'
                f'Minimum: {self.minimum}')


if __name__ == '__main__':
    f = Fuse()
    print("Reward 6 times.")
    for i in range(6):
        f.reward()
    print("Result\n" + str(f))
    if f:
        print("Flag is set!")
    else:
        print("Flag is not set!")
    print("Punish 5 times.")
    for i in range(5):
        f.punish()
    print("Result\n" + str(f))
    if f:
        print("Flag is set!")
    else:
        print("Flag is not set!")

