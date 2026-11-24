import java.util.Arrays;
import java.util.Base64;

/**
 * Measures writes beyond the decoder's calculated 98-byte output length while
 * keeping every write inside a real 160-byte Java array. This is a logical
 * boundary probe, not evidence of a Java-heap out-of-bounds write.
 */
public final class Base64TailProbe {
    private static volatile int sink;
    private static final int INPUT_LENGTH = 129;
    private static final int LOGICAL_OUTPUT_LENGTH = 98;
    private static final int DESTINATION_LENGTH = 160;
    private static final byte GUARD = (byte) 0x5a;

    private Base64TailProbe() {}

    static void warmDecoder() {
        byte[] source = new byte[192];
        Arrays.fill(source, (byte) 'A');
        byte[] destination = new byte[144];
        Base64.Decoder decoder = Base64.getDecoder();
        for (int i = 0; i < 60_000; i++) {
            sink ^= decoder.decode(source, destination);
        }
    }

    static byte[] malformedInput() {
        byte[] input = new byte[INPUT_LENGTH];
        Arrays.fill(input, (byte) 'A');
        input[INPUT_LENGTH - 1] = (byte) '=';
        return input;
    }

    public static void main(String[] args) {
        warmDecoder();
        byte[] destination = new byte[DESTINATION_LENGTH];
        Arrays.fill(destination, GUARD);
        String exception = "none";
        int decoded = -1;
        try {
            decoded = Base64.getDecoder().decode(malformedInput(), destination);
        } catch (RuntimeException error) {
            exception = error.getClass().getSimpleName();
        }

        int changedBeforeLogicalEnd = 0;
        int changedAfterLogicalEnd = 0;
        int firstAfter = -1;
        int lastAfter = -1;
        for (int i = 0; i < destination.length; i++) {
            if (destination[i] == GUARD) continue;
            if (i < LOGICAL_OUTPUT_LENGTH) {
                changedBeforeLogicalEnd++;
            } else {
                changedAfterLogicalEnd++;
                if (firstAfter < 0) firstAfter = i;
                lastAfter = i;
            }
        }
        System.out.printf(
            "{\"probe\":\"logical-tail\",\"java\":\"%s\",\"vm\":\"%s\","
                + "\"inputLength\":%d,\"logicalOutputLength\":%d,\"destinationLength\":%d,"
                + "\"decoded\":%d,\"exception\":\"%s\",\"changedBeforeLogicalEnd\":%d,"
                + "\"changedAfterLogicalEnd\":%d,\"firstChangedAfter\":%d,\"lastChangedAfter\":%d}%n",
            System.getProperty("java.version"), System.getProperty("java.vm.name"),
            INPUT_LENGTH, LOGICAL_OUTPUT_LENGTH, DESTINATION_LENGTH,
            decoded, exception, changedBeforeLogicalEnd, changedAfterLogicalEnd,
            firstAfter, lastAfter
        );
    }
}
