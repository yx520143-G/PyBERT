async (page) => {
  const legacy={
  "schema": 1,
  "commit": "1bc905d",
  "values": {
    "bit_rate": 25,
    "mod_type": "NRZ",
    "vod": 1.25,
    "pattern": "PRBS-7",
    "seed": 1,
    "tx_eq_sel": "Native",
    "rx_eq_sel": "Native",
    "inter_sel": "native",
    "ch_file": "",
    "ch_files": [],
    "renumber": false,
    "use_window": false,
    "lane_sel": 0,
    "l_ch": 0.5,
    "Z0": 100,
    "v0": 0.67,
    "Rdc": 0.1876,
    "R0": 1.452,
    "w0": 10000000,
    "Theta0": 0.02,
    "tx_sel": "native",
    "rx_sel": "native",
    "rs": 100,
    "cout": 0.5,
    "rin": 100,
    "cin": 0.5,
    "cac": 1,
    "rn": 0.01,
    "pn_mag": 0.01,
    "pn_freq": 11,
    "include_fext": false,
    "ctle_enable": true,
    "ctle_sel": "Native",
    "ctle_file": "",
    "peak_freq": 5,
    "rx_bw": 12,
    "peak_mag": 1.7,
    "rx_n_taps": 15,
    "rx_n_pre": 5,
    "gain": 0.1,
    "n_ave": 100,
    "decision_scaler": 0.5,
    "sum_ideal": true,
    "sum_bw": 12,
    "cdr_type": "Bang-Bang",
    "delta_t_ui": 0.001,
    "alpha": 0.01,
    "n_lock_ave": 500,
    "rel_lock_tol": 0.1,
    "lock_sustain": 500,
    "use_agc": true,
    "rx_use_viterbi": false,
    "rx_viterbi_symbols": 4,
    "nbits": 15000,
    "eye_bits": 10160,
    "nspui": 32,
    "debug": false,
    "f_max": 40,
    "f_step": 10,
    "impulse_length": 0,
    "thresh": 3,
    "pkg_enable": false,
    "pkg_group": "KR",
    "tx_pkg_case": "A1",
    "rx_pkg_case": "A1",
    "pkg_include_host": true,
    "tx_ibis_file": "",
    "rx_ibis_file": "",
    "tx_use_ts4": false,
    "rx_use_ts4": false,
    "tx_use_getwave": false,
    "rx_use_getwave": false,
    "rx_use_clocks": false,
    "tx_c0_min": 0,
    "ctle_enable_tune": true,
    "peak_freq_tune": 5,
    "rx_bw_tune": 12,
    "min_mag_tune": 2,
    "max_mag_tune": 12,
    "step_mag_tune": 1,
    "use_mmse": true,
    "rlm": 0.95,
    "ami_opt_trials": 100,
    "enable_com": false,
    "com_cfg_file": "",
    "peak_mag_tune": "",
    "trellis_err_select": 0,
    "trellis_pan_control": 0,
    "trellis_max_err": "",
    "tx_ibis_valid": "",
    "tx_ami_valid": "",
    "tx_dll_valid": "",
    "tx_ami_file": "",
    "tx_dll_file": "",
    "btn_sel_tx": "",
    "btn_view_tx": "",
    "btn_cfg_tx": "",
    "tx_ami_tap_tuners": "",
    "rx_ibis_valid": "",
    "rx_ami_valid": "",
    "rx_dll_valid": "",
    "rx_ami_file": "",
    "rx_dll_file": "",
    "btn_sel_rx": "",
    "btn_view_rx": "",
    "btn_cfg_rx": "",
    "rx_ami_tap_tuners": "",
    "tx_taps": [
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      }
    ],
    "tx_tap_tuners": [
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.05,
        "step": 0.025,
        "value": 0
      },
      {
        "enabled": true,
        "min_val": -0.1,
        "max_val": 0.1,
        "step": 0.05,
        "value": 0
      },
      {
        "enabled": true,
        "min_val": -0.2,
        "max_val": 0.2,
        "step": 0.1,
        "value": 0
      },
      {
        "enabled": false,
        "min_val": -0.2,
        "max_val": 0.2,
        "step": 0.1,
        "value": 0
      },
      {
        "enabled": false,
        "min_val": -0.1,
        "max_val": 0.1,
        "step": 0.05,
        "value": 0
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.05,
        "step": 0.025,
        "value": 0
      }
    ],
    "rx_taps": [
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 1
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": true,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      },
      {
        "enabled": false,
        "value": 0
      }
    ],
    "ffe_tap_tuners": [
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": true,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      },
      {
        "enabled": false,
        "min_val": -1,
        "max_val": 1,
        "step": 0.1
      }
    ],
    "dfe_tap_tuners": [
      {
        "enabled": true,
        "min_val": -0.2,
        "max_val": 0.4
      },
      {
        "enabled": true,
        "min_val": -0.15,
        "max_val": 0.15
      },
      {
        "enabled": true,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": true,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": true,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      },
      {
        "enabled": false,
        "min_val": -0.05,
        "max_val": 0.1
      }
    ]
  }
};
  const original=JSON.stringify(legacy),base='http://127.0.0.1:8770';
  await page.evaluate(original=>{for(const key of ['pybert-native-draft-v2','pybert-native-draft-v1','pybert-native-snapshot-v2','pybert-native-snapshot-v1','pybert-result-selection-v1'])localStorage.removeItem(key);localStorage.setItem('pybert-chain-draft-v1',original);},original);
  await page.reload();await page.waitForFunction(()=>JSON.parse(localStorage.getItem('pybert-native-draft-v2') || 'null')?.sources?.adapter_sha);
  const migrated=await page.evaluate(()=>({saved:JSON.parse(localStorage.getItem('pybert-native-draft-v2')),legacy:localStorage.getItem('pybert-chain-draft-v1'),error:window.PYBERT_WORKBENCH.migrationError()}));
  if(migrated.legacy!==original || migrated.saved.schema!==2 || migrated.saved.values.bit_rate!==25 || migrated.saved.values.vod!==1.25)throw new Error('PR7 migration/key preservation failed');
  const coverage=Object.entries(legacy.values).map(([key,value])=>({key,exact:JSON.stringify(migrated.saved.values[key])===JSON.stringify(value),retained:JSON.stringify(migrated.saved.retained_fields[key]?.value)===JSON.stringify(value)}));
  if(coverage.some(row=>!row.exact && !row.retained))throw new Error(JSON.stringify(coverage.filter(row=>!row.exact && !row.retained)));
  for(const key of ['adapter_sha','native_sha','prototype_sha'])if(!/^[a-f0-9]{40}$/.test(migrated.saved.sources[key]))throw new Error('Incomplete new source SHA');
  await page.screenshot({path:'output/playwright/20-full-pr7-migration.png'});
  const refused=[];
  for(const raw of ['invalid JSON',JSON.stringify({schema:999,values:{bit_rate:50}}),JSON.stringify({schema:2,values:{bit_rate:25},retained_fields:{future_physical_input:{value:123,blocking:false}}})]) {
    await page.evaluate(raw=>localStorage.setItem('pybert-native-draft-v2',raw),raw);await page.reload();
    await page.waitForFunction(()=>window.PYBERT_WORKBENCH?.migrationError());
    const value=await page.evaluate(()=>({raw:localStorage.getItem('pybert-native-draft-v2'),error:window.PYBERT_WORKBENCH.migrationError()}));
    if(raw.startsWith('invalid') || JSON.parse(raw).schema===999) {if(value.raw!==raw)throw new Error('Rejected storage overwritten');}
    else if(JSON.parse(value.raw).retained_fields.future_physical_input.blocking!==true)throw new Error('Unknown retained flag bypass');
    refused.push(value);
  }
  await page.screenshot({path:'output/playwright/21-unknown-retained-blocked.png'});
  await page.evaluate(()=>{localStorage.removeItem('pybert-native-draft-v2');localStorage.removeItem('pybert-chain-draft-v1');});await page.reload();
  await page.waitForFunction(()=>window.PYBERT_WORKBENCH && !window.PYBERT_WORKBENCH.migrationError() && !document.querySelector('#run').disabled);
  await page.evaluate(()=>{window.originalStorageSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw new DOMException('evidence injected unavailable storage','QuotaExceededError');};});
  await page.locator('#control-bit_rate').fill('26');await page.locator('#control-bit_rate').blur();
  await page.waitForFunction(()=>document.querySelector('#draft-status').textContent.includes('仅当前页面保留'));
  if(await page.evaluate(()=>window.PYBERT_WORKBENCH.getDraft().bit_rate)!==26)throw new Error('Storage failure lost input');
  await page.screenshot({path:'output/playwright/22-storage-failure-input-retained.png'});
  await page.evaluate(()=>{Storage.prototype.setItem=window.originalStorageSet;});
  await page.locator('#control-bit_rate').fill('27');await page.locator('#control-bit_rate').blur();
  await page.waitForFunction(()=>JSON.parse(localStorage.getItem('pybert-native-draft-v2')).values.bit_rate===27 && document.querySelector('#draft-status').textContent.includes('草稿已保留'));
  const final=await (await page.request.get(base+'/api/state')).json();if(final.runs.length || final.com_tasks.length)throw new Error('Migration started main/COM');
  return {authentic_pr7_field_count:coverage.length,coverage,migration:migrated,refused,storage_failure_kept_input:26,recovery_saved_input:27,main_calls:0,COM_calls:0};
}
