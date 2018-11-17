
import os
import sys
import tensorflow
import numpy
import pickle
from music21 import converter, instrument, note, chord, stream
from tensorflow.python.keras import utils
from tensorflow.python.keras.models import Sequential
from tensorflow.python.keras.layers import GRU

DATA_DIR = sys.argv[1]
PICKLE_NOTES = DATA_DIR + '/notes'                  # note file for where to read pickle data from
WEIGHTS = 'weights/' + DATA_DIR + '/' + sys.argv[2] # weight file to load from
NOTES = int(sys.argv[3])                            # num notes to generate
OUTPUT = 'output/' + DATA_DIR                       # directory to put the output
SEQ_LEN = int(sys.argv[4])                          # sequence length of inputs
BATCH = int(sys.argv[5])                            # batch size

def generateOutput(network_input, n_vocab, model, pitchnames):
    # Load the weights to each node
    start = numpy.random.randint(0, len(network_input)-1)
    int_to_note = dict((number, note) for number, note in enumerate(pitchnames))
    pattern = network_input[start]

    prediction_output = []
    for note_index in range(NOTES):
        prediction_input = numpy.reshape(pattern, (1, SEQ_LEN, 1))
        prediction_input = prediction_input / float(n_vocab)
        prediction = model.predict(prediction_input, batch_size=64, verbose=0)
        index = numpy.argmax(prediction)
        print(index)
        result = int_to_note[index]
        prediction_output.append(result)
        pattern = numpy.append(pattern, index)
        pattern = pattern[1:]

    return prediction_output

def getNetworkInputOuput(notes, n_vocab, pitchnames):
    """ Prepare the sequences used by the Neural Network """
    sequence_length = SEQ_LEN

     # create a dictionary to map pitches to integers
    note_to_int = dict((note, number) for number, note in enumerate(pitchnames))

    # create input sequences and the corresponding outputs
    network_input = []
    for i in range(0, len(notes) - sequence_length, 1):
        sequence_in = notes[i:i + sequence_length]
        network_input.append([note_to_int[char] for char in sequence_in])

    n_patterns = len(network_input)

    # reshape the input into a format compatible with LSTM layers
    return numpy.reshape(network_input, (n_patterns, sequence_length, 1))

def buildNetwork(network_input, n_vocab):
    model = Sequential() # linear stack of layers
    model.add(GRU(n_vocab, input_shape=(network_input.shape[1], network_input.shape[2]), activation='softmax'))
    model.compile(loss='categorical_crossentropy', optimizer='rmsprop')
    model.load_weights(WEIGHTS)
    return model

def createMidi(prediction_output):
    offset = 0
    output_notes = []
    # create note and chord objects based on the values generated by the model
    for pattern in prediction_output:
        # pattern is a chord
        if ('.' in pattern) or pattern.isdigit():
            notes_in_chord = pattern.split('.')
            notes = []
            for current_note in notes_in_chord:
                new_note = note.Note(int(current_note))
                new_note.storedInstrument = instrument.Piano()
                notes.append(new_note)
            new_chord = chord.Chord(notes)
            new_chord.offset = offset
            output_notes.append(new_chord)
        # pattern is a note
        else:
            new_note = note.Note(pattern)
            new_note.offset = offset
            new_note.storedInstrument = instrument.Piano()
            output_notes.append(new_note)

        # increase offset each iteration so that notes do not stack
        offset += 0.5

    midi_stream = stream.Stream(output_notes)

    if not os.path.exists(OUTPUT):
        os.makedirs(OUTPUT)
    midi_stream.write('midi', fp= OUTPUT + '/output.mid')

def generate():
    with open(PICKLE_NOTES, 'rb') as filepath:
        notes = pickle.load(filepath)

    n_vocab = len(set(notes))
    pitchnames = sorted(set(item for item in notes))
    network_input = getNetworkInputOuput(notes, n_vocab, pitchnames)
    prediction_output = generateOutput(network_input, n_vocab, buildNetwork(network_input, n_vocab), pitchnames)
    createMidi(prediction_output)

if __name__ == '__main__':
    generate()
