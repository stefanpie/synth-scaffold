#pragma once

#include <hls_stream.h>

template <const int in_size, const int out_size, const int BLOCK_SIZE_IN_ = 1,
          const int BLOCK_SIZE_OUT_ = 1, typename T>
void linear(T input[in_size], T output[out_size], T weight[out_size][in_size],
            T bias[out_size]) {
#pragma HLS INLINE off

    static_assert(in_size % BLOCK_SIZE_IN_ == 0,
                  "in_size must be divisible by BLOCK_SIZE_IN");
    static_assert(out_size % BLOCK_SIZE_OUT_ == 0,
                  "out_size must be divisible by BLOCK_SIZE_OUT");

    const int BLOCK_SIZE_OUT = BLOCK_SIZE_OUT_;
    const int BLOCK_SIZE_IN = BLOCK_SIZE_IN_;

#pragma HLS array_partition variable = input cyclic factor =                   \
    BLOCK_SIZE_IN dim = 1
#pragma HLS array_partition variable = output cyclic factor =                  \
    BLOCK_SIZE_OUT dim = 1

#pragma HLS array_partition variable = weight cyclic factor =                  \
    BLOCK_SIZE_OUT dim = 1
#pragma HLS array_partition variable = weight cyclic factor =                  \
    BLOCK_SIZE_IN dim = 2

#pragma HLS array_partition variable = bias cyclic factor =                    \
    BLOCK_SIZE_OUT dim = 1

    // block parallel linear layer
    // use temp sum
    T temp_sum[BLOCK_SIZE_OUT];
#pragma HLS ARRAY_PARTITION variable = temp_sum complete

    // set bias on output
BIAS_BLOCK_OUT:
    for (int a = 0; a < out_size; a += BLOCK_SIZE_OUT) {
#pragma HLS unroll off = true
#pragma HLS PIPELINE
    BIAS_WRITE:
        for (int b = 0; b < BLOCK_SIZE_OUT; b++) {
#pragma HLS unroll
            int tmp_idx = a + b;
            output[tmp_idx] = bias[tmp_idx];
        }
    }

BLOCK_OUT:
    for (int i = 0; i < out_size; i += BLOCK_SIZE_OUT) {
    BLOCK_IN:
        for (int j = 0; j < in_size; j += BLOCK_SIZE_IN) {

#pragma HLS PIPELINE
        // zero temp sum
        TEMP_SUM_ZERO_LOOP:
            for (int k = 0; k < BLOCK_SIZE_OUT; k++) {
#pragma HLS unroll
                temp_sum[k] = 0;
            }

        // compute temp sum
        SUM_OUTER:
            for (int k = 0; k < BLOCK_SIZE_OUT; k++) {
#pragma HLS unroll
            SUM_INNER:
                for (int l = 0; l < BLOCK_SIZE_IN; l++) {
#pragma HLS unroll
                    temp_sum[k] += weight[i + k][j + l] * input[j + l];
                }
            }

        WRITE_LOOP:
            for (int k = 0; k < BLOCK_SIZE_OUT; k++) {
#pragma HLS unroll
                output[i + k] += temp_sum[k];
            }
        }
    }
}

template <const int DIM_IN, const int DIM_OUT, typename T>
void vmm_unrolled_tile(T input[DIM_IN], T weight[DIM_OUT][DIM_IN],
                       T output[DIM_OUT]) {
#pragma HLS INLINE off

#pragma HLS array_partition variable = input complete
#pragma HLS array_partition variable = weight dim = 1 complete
#pragma HLS array_partition variable = weight dim = 2 complete
#pragma HLS array_partition variable = output complete

#pragma HLS pipeline II = 1

    for (int i = 0; i < DIM_OUT; i++) {
#pragma HLS UNROLL
        T acc = 0;
        for (int j = 0; j < DIM_IN; j++) {
#pragma HLS UNROLL
            acc += weight[i][j] * input[j];
        }
        output[i] = acc;
    }
}

template <const int in_size, const int out_size, const int BLOCK_SIZE_IN_ = 1,
          const int BLOCK_SIZE_OUT_ = 1, typename T>
void linear_v2(T input[in_size], T output[out_size],
               T weight[out_size][in_size], T bias[out_size]) {
#pragma HLS INLINE off

    static_assert(in_size % BLOCK_SIZE_IN_ == 0,
                  "in_size must be divisible by BLOCK_SIZE_IN");
    static_assert(out_size % BLOCK_SIZE_OUT_ == 0,
                  "out_size must be divisible by BLOCK_SIZE_OUT");

    const int BLOCK_SIZE_OUT = BLOCK_SIZE_OUT_;
    const int BLOCK_SIZE_IN = BLOCK_SIZE_IN_;

#pragma HLS array_partition variable = input cyclic factor =                   \
    BLOCK_SIZE_IN dim = 1
#pragma HLS array_partition variable = output cyclic factor =                  \
    BLOCK_SIZE_OUT dim = 1

#pragma HLS array_partition variable = weight cyclic factor =                  \
    BLOCK_SIZE_OUT dim = 1
#pragma HLS array_partition variable = weight cyclic factor =                  \
    BLOCK_SIZE_IN dim = 2

#pragma HLS array_partition variable = bias cyclic factor =                    \
    BLOCK_SIZE_OUT dim = 1

    typedef T chunk_input_t[BLOCK_SIZE_IN];
    typedef T chunk_weight_t[BLOCK_SIZE_OUT][BLOCK_SIZE_IN];
    typedef T chunk_output_t[BLOCK_SIZE_OUT];

    const int n_chunks_in = in_size / BLOCK_SIZE_IN;
    const int n_chunks_out = out_size / BLOCK_SIZE_OUT;

    hls::stream<chunk_input_t> input_stream;
    for (int i = 0; i < n_chunks_in; i++) {
#pragma HLS PIPELINE
        chunk_input_t input_chunk;
        for (int j = 0; j < BLOCK_SIZE_IN; j++) {
#pragma HLS UNROLL
            input_chunk[j] = input[i * BLOCK_SIZE_IN + j];
        }
        // input_stream.write(input_chunk);
        // write input stream repeatedly
        for (int k = 0; k < n_chunks_out; k++) {
            input_stream.write(input_chunk);
        }
    }

    hls::stream<chunk_weight_t> weight_stream;
    for (int i = 0; i < n_chunks_out; i++) {
        for (int j = 0; j < n_chunks_in; j++) {
#pragma HLS PIPELINE
            chunk_weight_t weight_chunk;
            for (int k = 0; k < BLOCK_SIZE_OUT; k++) {
#pragma HLS UNROLL
                for (int l = 0; l < BLOCK_SIZE_IN; l++) {
#pragma HLS UNROLL
                    weight_chunk[k][l] =
                        weight[i * BLOCK_SIZE_OUT + k][j * BLOCK_SIZE_IN + l];
                }
            }
            weight_stream.write(weight_chunk);
        }
    }

    hls::stream<chunk_output_t> bias_stream;
    for (int i = 0; i < n_chunks_out; i++) {
        chunk_output_t bias_chunk;

        for (int j = 0; j < BLOCK_SIZE_OUT; j++) {
#pragma HLS UNROLL
            bias_chunk[j] = bias[i * BLOCK_SIZE_OUT + j];
        }
        bias_stream.write(bias_chunk);
    }

    hls::stream<chunk_output_t> output_stream_partials;
    for (int i = 0; i < n_chunks_out; i++) {
        for (int j = 0; j < n_chunks_in; j++) {
#pragma HLS PIPELINE
            chunk_output_t output_chunk;
            vmm_unrolled_tile<BLOCK_SIZE_IN, BLOCK_SIZE_OUT>(
                input_stream.read(), weight_stream.read(), output_chunk);
            output_stream_partials.write(output_chunk);
        }
    }

    // finalize the output
    for (int i = 0; i < n_chunks_out; i++) {
        chunk_output_t output_chunk = output_stream_partials.read();
        for (int j = 0; j < BLOCK_SIZE_OUT; j++) {
#pragma HLS UNROLL
            output[i * BLOCK_SIZE_OUT + j] += output_chunk[j];
        }
        chunk_output_t bias_chunk = bias_stream.read();
        for (int j = 0; j < BLOCK_SIZE_OUT; j++) {
#pragma HLS UNROLL
            output[i * BLOCK_SIZE_OUT + j] += bias_chunk[j];
        }
    }
}