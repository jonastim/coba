import sys
import multiprocessing.pool

from multiprocessing import Manager
from threading       import Thread
from typing          import Sequence, Iterable, Any

from coba.config import CobaConfig, IndentLogger, CobaFatal
from coba.pipes  import Filter, Sink, Pipe, StopPipe, QueueSource, QueueSink

super_worker = multiprocessing.pool.worker

def worker(inqueue, outqueue, initializer=None, initargs=(), maxtasks=None, wrap_exception=False):
        try:
            super_worker(inqueue, outqueue, initializer, initargs, maxtasks, wrap_exception)
        except AttributeError:
            #we handle this exception because otherwise it is thrown and written to console
            #by handling it ourself we can prevent it from being written to console
            sys.exit(1000) #this is the exitcode we use to indicate when we're exiting due to import errors

multiprocessing.pool.worker = worker

class MultiprocessFilter(Filter[Iterable[Any], Iterable[Any]]):

    class Processor:

        def __init__(self, filters: Sequence[Filter], stdout: Sink, stdlog:Sink, n_proc:int) -> None:
            self._filter = Pipe.join(filters)
            self._stdout = stdout
            self._stdlog = stdlog
            self._n_proc = n_proc

        def process(self, item) -> None:
            
            #One problem with this is that the settings on the main thread's logger 
            #aren't propogated to this logger. For example, with_stamp and with_name.
            #A possible solution is to deep copy the CobaConfig.Logger, set its `sink`
            #property to the `stdlog` and then pass it to `Processor.__init__`.
            CobaConfig.Logger = IndentLogger(self._stdlog, with_name=self._n_proc > 1)

            try:
                self._stdout.write(self._filter.filter([item]))

            except StopPipe:
                pass

            except Exception as e:
                CobaConfig.Logger.log_exception(e)

            except KeyboardInterrupt:
                #When ctrl-c is pressed on the keyboard KeyboardInterrupt is raised in each
                #process. We need to handle this here because Processor is always ran in a
                #background process and receives this. We can ignore this because the exception will
                #also be raised in our main process. Therefore we simply ignore and trust the main to
                #handle the keyboard interrupt gracefully.
                pass

    def __init__(self, filters: Sequence[Filter], processes=1, maxtasksperchild=None) -> None:
        self._filters          = filters
        self._processes        = processes
        self._maxtasksperchild = maxtasksperchild

    def filter(self, items: Iterable[Any]) -> Iterable[Any]:

        if len(self._filters) == 0:
            return items

        try:
            with Manager() as manager:

                stdout_queue = manager.Queue() #type: ignore
                stdlog_queue = manager.Queue() #type: ignore

                stdout_writer, stdout_reader = QueueSink(stdout_queue), QueueSource(stdout_queue)
                stdlog_writer, stdlog_reader = QueueSink(stdlog_queue), QueueSource(stdlog_queue)

                class MyPool(multiprocessing.pool.Pool):

                    _missing_error_definition_error_is_new = True

                    def _join_exited_workers(self):

                        for worker in self._pool:
                            if worker.exitcode == 1000 and MyPool._missing_error_definition_error_is_new:
                                #this is a hack... This only works so long as we just 
                                #process one job at a time... This is true in our case.
                                #this is necessary because multiprocessing can get stuck 
                                #waiting for failed workers and that is frustrating for users.

                                MyPool._missing_error_definition_error_is_new = False

                                message = (
                                    "Coba attempted to process your benchmark on multiple processes and the pickle module was unable to "
                                    "find all the class definitions that it needed to unpickle the message. The two most common causes of "
                                    "this error are: 1) using a learner or simulation defined in a Jupyter Notebook cell or 2) a necessary "
                                    "class definition existing inside the if __name__=='__main__': clause in the main execution script. In "
                                    "either case there are two simple solutions: 1) evalute your benchmark in a single processed with no "
                                    "limit on child tasks or 2) define all you classes in a separate python script that is imported at when "
                                    "evaluating."                                    
                                )

                                CobaConfig.Logger.log(message)

                            if worker.exitcode is not None and worker.exitcode != 0:
                                #A worker exited in an uncontrolled manner and was unable to clean its job
                                #up. We therefore mark one of the jobs as "finished" but failed to prevent an
                                #infinite wait on a failed job to finish that is actually no longer running.
                                list(self._cache.values())[0]._set(None, (False, None))

                        return super()._join_exited_workers()

                with MyPool(self._processes, maxtasksperchild=self._maxtasksperchild) as pool:

                    # handle not picklable (this is handled by done_or_failed)
                    # handle empty list (this is done by checking result.ready())
                    # handle exceptions in process (unhandled exceptions can cause children to hang so we pass them to stderr)
                    # handle ctrl-c without hanging 
                    #   > don't call result.get when KeyboardInterrupt has been hit
                    #   > handle EOFError,BrokenPipeError errors with queue since ctr-c kills manager
                    # handle AttributeErrors

                    def done_or_failed(results_or_exception=None):

                        if isinstance(results_or_exception, Exception):
                            from coba.config import CobaConfig

                            if "Can't pickle" in str(results_or_exception) or "Pickling" in str(results_or_exception):
                                
                                message = (
                                    str(results_or_exception) + ". Coba attempted to process your Benchmark on multiple processes and "
                                    "the named class was not able to be pickled. This problem can be fixed in one of two ways: 1) "
                                    "evaluate the benchmark in question on a single process with no limit on the tasks per child or 2) "
                                    "modify the named class to be picklable. The easiest way to make the given class picklable is to "
                                    "add `def __reduce__ (self) return (<the class in question>, (<tuple of constructor arguments>))` to "
                                    "the class. For more information see https://docs.python.org/3/library/pickle.html#object.__reduce__."
                                )

                                CobaConfig.Logger.log(message)
                            else:
                                CobaConfig.Logger.log_exception(results_or_exception)
                            
                        stdout_writer.write([None])
                        stdlog_writer.write([None])

                    log_thread = Thread(target=Pipe.join(stdlog_reader, [], CobaConfig.Logger.sink).run)
                    log_thread.daemon = True
                    log_thread.start()

                    processor = MultiprocessFilter.Processor(self._filters, stdout_writer, stdlog_writer, self._processes)
                    result    = pool.map_async(processor.process, items, callback=done_or_failed, error_callback=done_or_failed, chunksize=1)

                    # When items is empty finished_callback will not be called and we'll get stuck waiting for the poison pill.
                    # When items is empty ready() will be true immediately and this check will place the poison pill into the queues.
                    if result.ready(): done_or_failed()

                    try:
                        for item in stdout_reader.read():
                            yield item
                        pool.close()
                    except (KeyboardInterrupt, Exception):
                        try:
                            pool.terminate()
                        except:
                            pass
                        raise
                    finally:

                        pool.join()
                        log_thread.join()

        except RuntimeError as e:
            #This happens when importing main causes this code to run again
            raise CobaFatal(str(e))