import argparse
import time

import numpy as np

import sphericart_torch
import torch

docstring = """
Benchmarks for the torch implementation of ``sphericart``.
Compares with E3NN if present.
"""

try:
    import jax
    import jax.numpy as jnp
    import e3nn_jax

    _HAS_E3NN = True
except ImportError:
    _HAS_E3NN = False


def sphericart_benchmark(
    l_max=10,
    n_samples=10000,
    n_tries=100,
    normalized=False,
    device="cpu",
    dtype=torch.float64,
    compare=False,
):
    print(
        f"**** Timings for l_max={l_max}, n_samples={n_samples}, n_tries={n_tries}, dtype={dtype}, device={device} ****"
    )
    xyz = torch.randn((n_samples, 3), dtype=dtype, device=device)
    sh_calculator = sphericart_torch.SphericalHarmonics(l_max, normalized=normalized)

    time_noderi = np.zeros(n_tries+10)
    for i in range(n_tries+10):
        elapsed = -time.time()
        sh_sphericart, _ = sh_calculator.compute(xyz, gradients=False)
        elapsed += time.time()
        time_noderi[i] = elapsed

    print(
        f" No derivatives: {time_noderi[10:].mean()/n_samples*1e9: 10.1f} ns/sample ± \
{time_noderi[10:].std()/n_samples*1e9: 10.1f} (std)"
    )

    time_deri = np.zeros(n_tries+10)
    for i in range(n_tries+10):
        elapsed = -time.time()
        sh_sphericart, dsh_sphericart = sh_calculator.compute(xyz, gradients=True)
        elapsed += time.time()
        time_deri[i] = elapsed

    print(
        f" Derivatives:    {time_deri[10:].mean()/n_samples*1e9: 10.1f} ns/sample ± \
{time_deri[10:].std()/n_samples*1e9: 10.1f} (std)"
    )

    # autograd
    xyz = xyz.clone().detach().type(dtype).to(device).requires_grad_()

    time_fw = np.zeros(n_tries+10)
    time_bw = np.zeros(n_tries+10)

    for i in range(n_tries+10):
        elapsed = -time.time()
        sh_sphericart, _ = sh_calculator.compute(xyz, gradients=False)
        elapsed += time.time()
        time_fw[i] = elapsed

        sph_sum = torch.sum(sh_sphericart)
        elapsed = -time.time()
        sph_sum.backward()
        elapsed += time.time()
        time_bw[i] = elapsed

    print(
        f" Autograd:       {time_fw[10:].mean()/n_samples*1e9: 10.1f} ns/sample ± \
{time_fw[10:].std()/n_samples*1e9: 10.1f} (std)"
    )
    print(
        f" Backprop:       {time_bw[10:].mean()/n_samples*1e9: 10.1f} ns/sample ± \
{time_bw[10:].std()/n_samples*1e9: 10.1f} (std)"
    )

    if compare and _HAS_E3NN:
        xyz_tensor = jnp.asarray(
            xyz[:, [1, 2, 0]].clone().detach().type(dtype).cpu().numpy()
        )
        """
        irreps = [f"1x{l}e + " for l in range(l_max+1)]
        total_irreps = ""
        for irrep in irreps:
            total_irreps += irrep
        irreps = e3nn_jax.Irreps(
            total_irreps[:-3]
        )
        """
        # Output only highest SH to be nice to e3nn, slower otherwise (uncomment above)
        irreps = e3nn_jax.Irreps(f"1x{l_max}e")

        if device == "cpu":
            for i in range(n_tries+10):
                elapsed = -time.time()
                sh_e3nn = e3nn_jax.spherical_harmonics(
                    irreps, xyz_tensor, normalize=normalized
                )
                elapsed += time.time()
                time_fw[i] = elapsed

            print(
                f" E3NN-JAX-FW:    {time_fw[10:].mean()/n_samples*1e9: 10.1f} ns/sample ± \
{time_fw[10:].std()/n_samples*1e9: 10.1f} (std)"
            )
        else:
            pass
    print("*********************************************************************************************")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=docstring)

    parser.add_argument("-l", type=int, default=10, help="maximum angular momentum")
    parser.add_argument("-s", type=int, default=1000, help="number of samples")
    parser.add_argument("-t", type=int, default=100, help="number of runs/sample")
    parser.add_argument(
        "--normalized",
        action="store_true",
        default=False,
        help="compute normalized spherical harmonics",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        default=False,
        help="compare timings with other codes, if installed",
    )

    args = parser.parse_args()

    # Run benchmarks
    sphericart_benchmark(
        args.l,
        args.s,
        args.t,
        args.normalized,
        device="cpu",
        dtype=torch.float64,
        compare=args.compare,
    )
    sphericart_benchmark(
        args.l,
        args.s,
        args.t,
        args.normalized,
        device="cpu",
        dtype=torch.float32,
        compare=args.compare,
    )

    if torch.cuda.is_available():
        sphericart_benchmark(
            args.l,
            args.s,
            args.t,
            args.normalized,
            device="cuda",
            dtype=torch.float64,
            compare=args.compare,
        )
        sphericart_benchmark(
            args.l,
            args.s,
            args.t,
            args.normalized,
            device="cuda",
            dtype=torch.float32,
            compare=args.compare,
        )
