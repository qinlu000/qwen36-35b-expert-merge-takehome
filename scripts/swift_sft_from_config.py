"""Native Swift Python entry: retain dict values that its CLI cannot parse."""
import json
import sys

from swift.arguments import SftArguments
from swift.pipelines import sft_main
from swift.utils import parse_args_from_dict

from sft_eval_loss import enable_liger_eval_loss


if __name__ == '__main__':
    with open(sys.argv[1]) as stream:
        config = json.load(stream)
    if config.get('use_liger_kernel'):
        enable_liger_eval_loss()
    args = parse_args_from_dict(SftArguments, config)
    sft_main(args)
