import mcr2.functional as F
import opt_einsum
import torch

from .abstract import CodingRate


class TranslationInvariantCodingRate(CodingRate):
    def R(self, Z):
        """
        Computes the coding rate of Z.
        NOTE: Only an accurate measure of the coding rate if the data is FFTed beforehand.
        You can do this with mcr.functional.fft2(Z).

        Args:
            Z: data matrix, (N, C, H, W)
            input_in_fourier_basis: whether the input is in Fourier basis; e.g. already FFTed

        Returns:
            The coding rate of Z.
        """
        N, C, H, W = Z.shape  # (N, C, H, W)
        ZTZ = F.gram_translation_invariant(Z)  # (H, W, C, C)
        alpha = C / (N * self.eps_sq)
        I = torch.eye(C).view(1, 1, C, C)  # (1, 1, C, C)
        Sigma_hat = I + alpha * ZTZ  # (H, W, C, C)
        return torch.sum(F.logdet(Sigma_hat)) / 2.0  # ()

    def Rc(self, Z, Pi):
        """
        Computes the segmented coding rate of Z with respect to a class information matrix Pi.
        NOTE: Only an accurate measure of the coding rate if the data is FFTed beforehand.
        You can do this with mcr.functional.fft2(Z).

        Args:
            Z: data matrix, (N, C, H, W)
            Pi: class information matrix, (N, K)
            input_in_fourier_basis: whether the input is in Fourier basis; e.g. already FFTed

        Returns:
            The segmented coding rate of Z with respect to Pi.
        """
        N, C, H, W = Z.shape  # (N, C, H, W)
        N, K = Pi.shape  # (N, K)
        ZTZ_per_class = F.gram_per_class_translation_invariant(Z, Pi)  # (K, H, W, C, C)
        N_per_class = torch.sum(Pi, axis=0)  # (K, )
        gamma_per_class = N_per_class / N  # (K, )
        alpha_per_class = torch.where(  # stops divide by 0 errors
            N_per_class > 0,
            C / (self.eps_sq * N_per_class),  # (K, )
            torch.tensor(0.0)  # ()
        )  # (K, )
        I = torch.eye(C).view(1, 1, 1, C, C)  # (1, 1, 1, C, C)
        Sigma_hat_per_class = I + alpha_per_class.view(K, 1, 1, 1, 1) * ZTZ_per_class  # (K, H, W, C, C)
        logdets_per_class = torch.sum(
            F.logdet(Sigma_hat_per_class),  # (K, H, W)
            dim=(1, 2)
        )  # (K, )
        return torch.sum(gamma_per_class * logdets_per_class) / 2.0  # ()

    def DeltaR(self, Z, Pi):
        """
        Computes the coding rate reduction of Z with respect to a class information matrix Pi.
        NOTE: Only an accurate measure of the coding rate if the data is FFTed beforehand.
        You can do this with mcr.functional.fft2(Z).

        Args:
            Z: data matrix, (N, C, H, W)
            Pi: class information matrix, (N, K)
            input_in_fourier_basis: whether the input is in Fourier basis; e.g. already FFTed

        Returns:
            The coding rate reduction of Z with respect to Pi.
        """
        return self.R(Z) - self.Rc(Z, Pi)