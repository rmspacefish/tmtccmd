from abc import abstractmethod


class FrontendBase:

    @abstractmethod
    def start(self, args: any):
        """
        Start the frontend.
        :return:
        """