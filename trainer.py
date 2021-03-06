from queue import Queue
from random import shuffle, choice
from threading import Thread, Event, Lock

from board import Board
from player import NNPlayer


class OddPopulationError(Exception):
    def __init__(self):
        super().__init__("please use an even population size so every bot is guaranteed a game each sub generation")


def trainer_thread(queue, thread_id, quit_event, queue_lock):
    """
    A thread tha pulls two NNPlayers from a queue and plays a game with them, updates their elo and puts them in a
    separate queue
    :param queue: a queue of bots that have not player yet
    :type queue: Queue
    :param thread_id: the thread id
    :type thread_id: int
    :param quit_event: an event to tell the thread when to quit
    :type quit_event: Event
    :param queue_lock: a lock to make sure that the last player is not taken between the two gets
    """
    print(f"Thread {thread_id} started")
    while not quit_event.is_set():
        while queue.qsize() > 1:
            with queue_lock:
                if queue.qsize() < 2:
                    break
                player_one = queue.get()
                player_two = queue.get()
            board = Board(player_one, player_two)
            NNPlayer.update_elo(*board.play())
    print(f"Thread {thread_id} quitting")
    return


def run_generation(players, sub_generations, player_queue):
    """
    runs a number of generations with each bot playing one game each generation.
    :param players: an array of the current population
    :type players: NNPlayer[]
    :param sub_generations: how many games to play each generation
    :type sub_generations: int
    :param player_queue: the player que to pass players to the game threads, past in as needed when creating threads
    :type player_queue: Queue
    :return:
    :rtype:
    """

    for sub_generation in range(sub_generations):
        shuffle(players)
        for player in players:
            player_queue.put(player)

        while player_queue.qsize() > 1:
            pass
    return players


def train(population_size, fraction_kept, generations, sub_generations, mutation_rate, threads=10):
    """
    trains the neural nets using genetic algorithem for a given number of generations

    :param population_size: the number of bots to have in each generation
    :type population_size: int
    :param fraction_kept: proportion of bots to cull each generation
    :type fraction_kept: float
    :param generations: number of generations to train for
    :type generations: int
    :param sub_generations: number of games each generation
    :type sub_generations: int
    :param mutation_rate: the probability of mutation
    :type mutation_rate: float
    :param threads: number of threads
    :type threads: int
    :return: the best bot after generations generations
    :rtype: NNPlayer
    """

    if population_size % 2 != 0:
        raise OddPopulationError

    quit_event = Event()
    queue_lock = Lock()
    players = [NNPlayer() for _ in range(population_size)]
    live_threads = []
    try:
        player_queue = Queue()
        for thread_id in range(threads):
            thread = Thread(target=trainer_thread, args=(player_queue, thread_id, quit_event, queue_lock))
            thread.setDaemon(True)
            thread.start()
            live_threads.append(thread)

        for generation in range(generations):
            print(f"generation {generation} {players[0]}")
            players = run_generation(players=players, sub_generations=sub_generations, player_queue=player_queue)
            players.sort(reverse=True)
            players = players[:int(len(players) * fraction_kept)]
            i = 0
            while len(players) < population_size:
                if i % 2 == 0:
                    new_player = choice(players).copy()  # type: NNPlayer
                    new_player.mutate(mutation_rate)
                else:
                    new_player = NNPlayer()

                players.append(new_player)
    finally:
        quit_event.set()
        for thread in live_threads:
            thread.join()
        return players


if __name__ == '__main__':
    from player import HumanPlayer

    trained = train(population_size=100, fraction_kept=0.2, generations=100, sub_generations=2, mutation_rate=0.5,
                    threads=10)
    best = trained[0]
    next_best = trained[1]
    print("\n\nTraining Complete\n\n")
    print(f"best elo is {best.elo}\n\n")
    best.save()
    human = HumanPlayer()
    board = Board(best, human)
    print(board.play())
